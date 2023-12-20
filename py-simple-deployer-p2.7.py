import subprocess
import os
import json
from collections import namedtuple
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


Command = namedtuple("Command", ["name", "steps", "optional"])


class ErrorDetails:
    def __init__(self, code, stderr, command, step):
        self.code = code
        self.stderr = stderr
        self.command = command
        self.step = step


class CommandResult:
    def __init__(self, error, details=None):
        self.error = error
        self.details = details


def get_param(parm_name, default_value=None):
    param_value = os.getenv(parm_name, default_value)
    if param_value:
        return param_value
    raise Exception("Missing param {}".format(parm_name))


PROJECTS_DIR = get_param("PROJECTS_DIR")
SETTINGS_FILENAME = get_param(
    "SETTINGS_FILENAME", "lhs-deployer-settings.json")
HOST = get_param("HOST", "0.0.0.0")
PORT = get_param("PORT", "8069")


class Deployer:
    def __init__(self, base_path):
        self.base_path = base_path
        self._settings = {}
        self._commands = []
        self._parse_settings()

    def _parse_settings(self):
        settings_path = os.path.join(self.base_path, SETTINGS_FILENAME)
        with open(settings_path) as f:
            self._settings = json.load(f)
        parsed_commands = self._settings.get("commands", [])
        for command in parsed_commands:
            self._commands.append(
                Command(command["name"], command["steps"], command.get("optional", False)))

    def _run_command(self, command):
        os.chdir(self.base_path)
        for step in command.steps:
            step_args = step.split()
            command_out = subprocess.Popen(
                step_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = command_out.communicate()
            if command_out.returncode and not command.optional:
                return CommandResult(True, ErrorDetails(code=command_out.returncode, stderr=err,
                                                        command=command.name, step=step))
        return CommandResult(error=False)

    def deploy(self, checkout_first):
        commands_to_run = self._commands
        if checkout_first:
            commands_to_run = [
                Command("Checkout new code", ["git pull"], False)] + self._commands
        for command in commands_to_run:
            result = self._run_command(command)
            if result.error:
                break
        return result


class DeployerOrchestrator:
    _deployers = {}

    def __init__(self, base_dir):
        self.base_dir = base_dir
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

    def deploy(self, project_name, checkout_first):
        deployer = self._deployers.get(project_name)
        if not deployer:
            return ({"message": "project '{0}' exist".format(project_name)}, 404)
        result = deployer.deploy(checkout_first)
        if result.error:
            return ({"message": "Encountered an error while running. Details:\nCommand: {0}, Step: '{1}'\n{2}: {3}".format(result.details.command, result.details.step, result.details.code, result.details.stderr)}, 500)
        else:
            return ({"message": "Success"},)


class Server(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.orchestrator = DeployerOrchestrator(PROJECTS_DIR)
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def respond_text(self, content, response_code=200, content_type="text/html"):
        self.send_response(response_code)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(content + "\n")

    def respond_json(self, data, response_code=200):
        self.respond_text(json.dumps(data), response_code,
                          content_type="application/json")

    def get_clear_path(self, path):
        return path.split("?")[0][1:]

    def do_POST(self):
        try:
            content_len = int(self.headers.get('Content-Length'))
            post_body = json.loads(
                self.rfile.read(content_len).decode('utf-8'))
        except ValueError:
            post_body = {}
        except TypeError:
            post_body = {}

        project = post_body.get("project")
        checkout = bool(post_body.get("checkout")) or True
        if project:
            self.respond_json(*self.orchestrator.deploy(project, checkout))
        else:
            self.respond_json({"message": "Need to specify the project"}, 400)


server = HTTPServer((HOST, int(PORT)), Server)
server.serve_forever()
server.server_close()
