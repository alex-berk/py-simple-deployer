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
PROJECTS_DIR=$(get_user_input "Path to the directory with projects" "${PWD%/*}")
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

SERVICE_FILE_CONTENT="[Unit]
Description=SimpleDeploy Daemon
After=network-online.target
[Service]
Type=simple
Environment=\"PROJECTS_DIR=$PROJECTS_DIR\"
Environment=\"SETTINGS_FILENAME=$SETTINGS_FILENAME\"
Environment=\"BRANCH_NAME=$BRANCH_NAME\"
Environment=\"HOST=$HOST\"
Environment=\"PORT=$PORT\"
Environment=\"UUID=$UUID\"
ExecStart=$PYTHON_EXECUTABLE $(pwd)/$DEPLOYER_FILE
Restart=on-failure

[Install]
WantedBy=multi-user.target"

echo "$SERVICE_FILE_CONTENT" > /etc/systemd/system/simpledeploy.service

systemctl daemon-reload
systemctl start simpledeploy
if systemctl is-active --quiet simpledeploy; then
	echo "SimpleDeployer is Running"
else
	echo "Something went wrong..."
fi
