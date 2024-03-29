import subprocess
import os
import json
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler


PROJECTS_DIR = os.getenv("PROJECTS_DIR")
SETTINGS_FILENAME = os.getenv(
    "SETTINGS_FILENAME", "lhs-deployer-settings.json")
BRANCH_NAME = os.getenv("BRANCH_NAME", "")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", "8069")

if not PROJECTS_DIR:
    raise Exception(f"Missing env param PROJECTS_DIR")


@dataclass
class Command:
    name: str
    steps: list[str]
    optional: bool


@dataclass
class ErrorDetails:
    code: int
    stderr: str
    command: str
    step: str


@dataclass
class CommandResult:
    error: bool
    details: ErrorDetails | None = None


class Deployer:
    def __init__(self, base_path) -> None:
        self.base_path = base_path
        self._settings = {}
        self._commands: list[Command] = []
        self._parse_settings()

    def _parse_settings(self) -> None:
        settings_path = os.path.join(self.base_path, SETTINGS_FILENAME)
        with open(settings_path) as f:
            self._settings = json.load(f)
        parsed_commands = self._settings.get("commands", [])
        for command in parsed_commands:
            self._commands.append(
                Command(command["name"], command["steps"], command.get("optional", False)))

    def _run_command(self, command: Command) -> CommandResult:
        os.chdir(self.base_path)
        for step in command.steps:
            step_args = step.split()
            command_out = subprocess.run(
                step_args, capture_output=True, text=True)
            if command_out.returncode and not command.optional:  # check for non-zero return code
                return CommandResult(True, ErrorDetails(code=command_out.returncode, stderr=command_out.stderr,
                                                        command=command.name, step=step))
        return CommandResult(error=False)

    def deploy(self, pull_first: bool, checkout_branch: str) -> CommandResult | None:
        commands_to_run = self._commands
        # todo: consider reloading after pulling new code
        if checkout_branch:
            commands_to_run.insert(0, Command(
                "Checkout default branch", [f"git checkout {BRANCH_NAME}"], True))
        if pull_first:
            commands_to_run.insert(0, Command(
                "Pull new code", ["git pull"], False))

        for command in commands_to_run:
            result = self._run_command(command)
            if result.error:
                break
        return result


class DeployerOrchestrator:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self._deployers = {}
        self._find_project_settings()

    def _find_project_settings(self):
        try:
            _, project_dirs, _ = next(os.walk(self.base_dir))
        except StopIteration:
            return ("Couldn't find the folder with projects:",
                    self.base_dir)
        for project_dir in project_dirs:
            path = os.path.join(self.base_dir, project_dir)
            settings_path = os.path.join(path, SETTINGS_FILENAME)
            if os.path.exists(settings_path):
                self._deployers[project_dir] = Deployer(path)

    def run_deployer(self, project_name: str, pull_first: bool, checkout_branch: str) -> (dict, int):
        deployer = self._deployers.get(project_name)
        if not deployer:
            return ({"message": f"project '{project_name}' doesn't exist"}, 404)
        result = deployer.deploy(pull_first, checkout_branch)
        if result.error:
            return ({"message": f"Encountered an error while running. Details:\nCommand: {result.details.command}, Step: '{result.details.step}'\n{result.details.code}: {result.details.stderr}"}, 500)

        return ({"message": "Success"},)


class Server(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.orchestrator = DeployerOrchestrator(PROJECTS_DIR)
        super().__init__(*args, **kwargs)

    def respond_text(self, content, response_code=200, content_type="text/html"):
        self.send_response(response_code)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(bytes(content + "\n", "utf-8"))

    def respond_json(self, data, response_code=200):
        self.respond_text(json.dumps(data), response_code,
                          content_type="application-json")

    def do_POST(self):
        try:
            content_len = int(self.headers.get('Content-Length'))
            post_body = json.loads(
                self.rfile.read(content_len).decode('utf-8'))
        except json.decoder.JSONDecodeError:
            post_body = {}
        except TypeError:
            post_body = {}

        project = post_body.get("project")
        pull = bool(post_body.get("pull", True))
        if not project:
            self.respond_json({"message": "Need to specify the project"}, 400)

        self.respond_json(
            *self.orchestrator.run_deployer(project, pull, BRANCH_NAME))

    def do_GET(self):
        self.respond_json({"health": "ok"})


server = HTTPServer((HOST, int(PORT)), Server)
server.serve_forever()
server.server_close()
