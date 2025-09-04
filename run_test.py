import os
import subprocess
import sys
import json

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_numeric_input(prompt):
    while True:
        try:
            value = int(input(prompt))
            if value > 0: return value
            else: print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main():
    clear_screen()

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        requests = config.get('requests', [])
        if not requests:
            print("Error: 'config.json' is empty or missing the 'requests' list. Exiting.")
            sys.exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading 'config.json': {e}. Exiting.")
        sys.exit(1)

    print("First, let's establish a baseline for your tests.")
    peak_users = get_numeric_input("Around how many concurrent users do you expect at your peak? ")

    base_url = input("\nPlease enter the API base URL (e.g., https://test-api.k6.io):\n> ")
    auth_token = input("\nPlease paste the Bearer Token (or press Enter if none):\n> ")

    print("\nWhich API request would you like to test?")
    for i, req in enumerate(requests):
        print(f"{i + 1}) {req['name']} ({req['method']})")

    req_choice_idx = get_numeric_input(f"Enter number (1-{len(requests)}): ") - 1
    if not 0 <= req_choice_idx < len(requests):
        print("Invalid choice. Exiting.")
        sys.exit(1)

    chosen_request = requests[req_choice_idx]

    print("\nWhich type of test would you like to run?")
    print("1) Smoke  2) Load  3) Stress  4) Spike  5) Soak")
    test_choice = input("Enter number(s), separated by commas (e.g., 1,3): ")

    test_map = {"1": "smoke", "2": "load", "3": "stress", "4": "spike", "5": "soak"}
    tests_to_run = [test_map[c.strip()] for c in test_choice.split(',') if c.strip() in test_map]

    if not tests_to_run:
        print("No valid tests selected. Exiting.")
        sys.exit(1)

    print("\n--- Starting web server... ---")
    subprocess.run(["docker", "compose", "up", "-d", "--build", "web-server"], check=True)
    print("Web server is running on http://localhost:8069/dashboardgenerator.html")

    for test_type in tests_to_run:
        print("\n=========================================================")
        print(f"  Starting: {test_type.title()} Test on '{chosen_request['name']}'")
        print(f"  Scaled for {peak_users} peak VUs")
        print("=========================================================\n")

        env_vars = {
            "BASE_URL": base_url,
            "ENDPOINT": chosen_request['endpoint'],
            "REQUEST_METHOD": chosen_request['method'],
            "AUTH_TOKEN": auth_token,
            "DATA_FILE": chosen_request.get('dataFile', ''),
            "TEST_TYPE": test_type,
            "PEAK_VUS": str(peak_users),
            "REQUEST_PAYLOAD": json.dumps(chosen_request.get('payload', {})),
            "CONTENT_TYPE": chosen_request.get('contentType', 'multipart/form-data'),
            "REQUEST_HEADERS": json.dumps(chosen_request.get('headers', {})),
            "QUERY_PARAMS": json.dumps(chosen_request.get('queryParams', {})),
            "EXPECTED_STATUS": str(chosen_request.get('expectedStatus', 200))
        }

        command = ["docker", "compose", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}"]
        for key, value in env_vars.items():
            command.extend(["-e", f"{key}={value}"])
        command.append("k6")

        try:
            subprocess.run(command, check=True)

            # --- FIX STARTS HERE ---
            # Loop through all files in the results directory and make them
            # world-readable (permission 644) so the Nginx container can serve them.
            results_dir = './results'
            if os.path.isdir(results_dir):
                for filename in os.listdir(results_dir):
                    file_path = os.path.join(results_dir, filename)
                    if os.path.isfile(file_path):
                        os.chmod(file_path, 0o644)
            # --- FIX ENDS HERE ---

            print(f"\n--- {test_type.title()} Test Finished ---")
            print("--- Dashboard data updated. Refresh your browser. ---")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"\n--- An error occurred during the {test_type.title()} Test ---")
            break

    print("\nAll selected tests have finished. To stop the web server, run: docker compose down")

if __name__ == "__main__":
    main()