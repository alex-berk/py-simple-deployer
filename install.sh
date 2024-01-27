#! /bin/bash

function get_user_input() {
	# expects prompt text and optional default value
	prompt_text=$1
	default_value=$2
	if [ ! -z $default_value ]; then
		prompt="$prompt_text [$default_value]: "
	else
		prompt="$prompt_text: "
	fi

	read -p "$prompt" inp
	if [ -z $inp ]; then
		inp=$default_value
	fi
	echo "$inp"
}

PYTHON_VERSION=$(get_user_input "Do you want to use python 3 or 2?" "3.11")
PROJECTS_DIR=$(get_user_input "Path to the directory with projects" "$HOME/projects")
SETTINGS_FILENAME=$(get_user_input "Name for the file with deploy settings" "lhs-deployer-settings.json")
HOST=$(get_user_input "Host" "0.0.0.0")
PORT=$(get_user_input "Port" "8069")
BRANCH_NAME=$(get_user_input "Branch to checkout (optional)")
UUID=$(uuidgen)

VERSIONS_2=("2" "2.7" "two")
if [[ ${VERSIONS_2[@]} =~ $PYTHON_VERSION ]]; then
	PYTHON_VERSION="2.7"
	PYTHON_EXECUTABLE=$(which python)
else
	PYTHON_VERSION="3.11"
	PYTHON_EXECUTABLE=$(which python3)
fi
DEPLOYER_FILE="py-simple-deployer-p$PYTHON_VERSION.py"

SERVICE_FILE_CONTENT="[Unit]\nDescription=SimpleDeploy Daemon\nAfter=network-online.target\n\n[Service]\nType=simple\nEnvironment=\"PROJECTS_DIR=$PROJECTS_DIR\"\nEnvironment=\"SETTINGS_FILENAME=$SETTINGS_FILENAME\"\nEnvironment=\"BRANCH_NAME=$BRANCH_NAME\"\nEnvironment=\"HOST=$HOST\"\nEnvironment=\"PORT=$PORT\"\nEnvironment=\"UUID=$UUID\"\nExecStart=$PYTHON_EXECUTABLE $(pwd)$DEPLOYER_FILE\nRestart=on-failure\n\n[Install]\nWantedBy=multi-user.target\n"
echo $SERVICE_FILE_CONTENT > /etc/systemd/system/simpledeploy.service

systemctl daemon-reload
systemctl start simpledeploy
systemctl is-active --quiet simpledeploy \ 
	&& echo "SimpleDeployer is Running" \
	# && echo "Your personal UUID is $UUID" \
	# && echo "You will need it to access the service from CI service" \
	|| echo "Something went wrong..."
