# Simple Deployer

A simple deployer written in plain Python without any external dependencies to manage home projects through GitHub Actions.

## Getting started

In order for application to always run in the background you'll need to add it as service. Here's an example on how to do it on Ubuntu:

1. Copy `py-simple-deployer` script of necessary python version on your deployment server. Version 2.7 comes with your distro by default, but version 3.11 will be more stable.

2. Update `PROJECTS_DIR` with a path to the directory with your projects in the script file.

3. Create a file `simpledeploy.service` in the `/etc/systemd/system` directory with this content:

```
[Unit]
Description=SimpleDeploy Daemon
After=network-online.target

[Service]
Type=simple
Environment="PROJECTS_DIR=<path to your projects dir>"
ExecStart=<path to your python executable> <path to the script>
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Set path to your projects in `PROJECTS_DIR` environment variable.
Replace `<path to your python executable>` with path to your python executable (you can check it with command `which python`), and `<path to the script>` with location of the main script (`pye-simple-deployer-pX.X.py`).
You can check the example of the file [here](https://github.com/alex-berk/py-simple-deployer/blob/main/simpledeploy.service).

4. Restart your systemctl daemon with command `systemctl daemon-reload`
5. Start the service by running command `service simpledeploy start`
6. Check that the service is running with command `service simpledeploy status`

## Usage

On the server all your projects have to be stored in one directory. Path to that directory should be stored in the `PROJECTS_DIR` variable in the main script file (`py-simple-deployer-pX.X.py`)

### Adding a deploy config

In the root of your project create a `lhs-deployer-settings.json` file.
It should have an array of `commands`. Each command should have a `name` and `steps` fields. Additionally, it can have an `optional` field.
`name` - string; name of the step for output
`steps` - arrays of strings; commands that should be run in this step
`optional` - optional boolean; if `true`, errors on this step can be skipped
Example of valid config file:

```
{
  "commands": [
    {
      "name": "docker cleanup",
      "steps": ["docker stop container-name", "docker rm container-name"],
      "optional": true
    },
    { "name": "build", "steps": ["pipenv run build"] },
    { "name": "start", "steps": ["pipenv run start"] }
  ]
}
```

### Setting up a Github Action

In Github create a repository secret `DEPLOYER_HOST` with a hostname of your server. You can do it by going to your repository page on GitHub and going "Settings" -> "Secrets and variables" -> "Actions" -> "Repository secrets".
In the root of your project, create a file `.github/workflows/deploy.yml`
Here's an example of an action that will call deployment service on each merge to `main` branch:

```
name: Deploy

on:
  pull_request:
    types:
      - closed
    branches:
      - main

jobs:
  deploy:
    name: Deploy
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: "Post deploy request"
        run: curl --fail-with-body --silent ${{ secrets.DEPLOYER_HOST }} -X POST --data '{"project":"${{ github.event.repository.name }}"}'

```
