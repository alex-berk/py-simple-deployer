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

PROJECTS_DIR=$(get_user_input "Path to the directory with projects" "~/projects")
SETTINGS_FILENAME=$(get_user_input "Name for the file with deploy settings"  "lhs-deployer-settings.json")
HOST=$(get_user_input "Host"  "0.0.0.0")
PORT=$(get_user_input "Port"  "8069")
BRANCH_NAME=$(get_user_input "Branch to checkout (optional)")
UUID=$(uuidgen)

echo "Provided inputs:"
echo $PROJECTS_DIR $SETTINGS_FILENAME $BRANCH_NAME $HOST:$PORT $UUID
