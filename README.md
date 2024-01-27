# Simple Deployer

A simple deployer written in plain Python without any external dependencies to manage home projects through GitHub Actions.

## Installation

In order for application to always run in the background it will need to add itself as service.
To start the installation process, run `install.sh` script with `sudo` privileges.

Installer will ask you to provide some variables:
* Your preffered python version. Python 3.11 version might be more stable, but 2.7 might be the version that comes as a default with your distro
* Project direcrory - folder where deployer service will be looking for subdirectories with deploy config file
* Name of the deploy config file. Default is `lhs-deployer-settings.json`, located in the root of each project
* Host and Port to for the deployer to listen
* (optional) Name of the branch to checkout each time deployer is running

After that it'll create a `simpledeploy.service` in the `/etc/systemd/system` directory with content like that:

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

After that it will restart your systemctl daemon and start simpledeplyer process. You should see the message that installation was successful and simpledeploy service is now running.
You can check it by running `service simpledeploy status` or sending get request to the endpoint (default is `localhost:8069`).

## Usage

On the server all your projects have to be stored in one directory. Path to that directory should be stored in the `PROJECTS_DIR` that you specified during installation process. If you need to change the direcory, you can edit it in `/etc/systemd/system/simpledeploy.service`.

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
