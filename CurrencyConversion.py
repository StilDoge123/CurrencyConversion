import subprocess
from datetime import datetime
import argparse
from forex_python.converter import CurrencyCodes
import sys
import json
import os
import requests


def install_requirements():
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    if result.returncode != 0:
        print("Failed to install required packages")
        sys.exit(result.returncode)


def is_date_valid(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if date <= datetime.today():
            return date
        return False
    except ValueError:
        return False


def is_amount_valid(amount):
    try:
        parts = amount.split(".")
        if len(parts) == 2 and len(parts[1]) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return True
        print("Please enter a valid amount")
        return False
    except:
        print("Please enter a valid amount")
        return False


def is_currency_code_valid(code):
    currency_codes = CurrencyCodes()
    if currency_codes.get_currency_name(code.upper()) is not None:
        return True
    print("Please enter a valid currency code")
    return False


def get_amount():
    while True:
        amount = input()
        if amount.upper() == "END":
            sys.exit()
        if is_amount_valid(amount):
            return amount


def get_currency_code():
    while True:
        code = input()
        if code.upper() == "END":
            sys.exit()
        if is_currency_code_valid(code):
            return code.upper()


def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r') as json_file:
        return json.load(json_file)


get_exchange_rates_called = False


def get_exchange_rates(api_key, date, base_currency, target_currency):
    url = 'https://api.fastforex.io/historical'
    params = {
        'api_key': api_key,
        'date': date,
        'from': base_currency
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    global get_exchange_rates_called
    get_exchange_rates_called = True

    file_name = 'cached_exchange_rates.json'

    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            try:
                records = json.load(file)
            except json.JSONDecodeError:
                records = []
    else:
        records = []

    new_record = {
        "date": date,
        "base_currency": base_currency,
        "results": response.json()['results']
    }
    if new_record not in records:
        records.append(new_record)

    with open(file_name, 'w') as file:
        json.dump(records, file, indent=4)

    return response.json()['results'][target_currency]


def get_cached_exchange_rates(date, base_currency, target_currency):
    file_name = 'cached_exchange_rates.json'
    if os.path.isfile(file_name):
        with open(file_name, 'r') as json_file:
            cached_exchange_rates = json.load(json_file)
    else:
        cached_exchange_rates = {}

    for entry in cached_exchange_rates:
        if entry['date'] == date and entry['base_currency'] == base_currency:
            results = entry['results']
            if target_currency in results:
                return results[target_currency]
    return None


def save_to_output_file(date, amount, base_currency, target_amount, target_currency):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'output.json')

    new_entry = {
        "date": date,
        "amount": float(amount),
        "base_currency": base_currency,
        "target_amount": target_amount,
        "target_currency": target_currency
    }

    if os.path.isfile(output_path):
        with open(output_path, 'r') as json_file:
            existing_data = json.load(json_file)
    else:
        existing_data = []

    existing_data.append(new_entry)
    with open(output_path, 'w') as json_file:
        json.dump(existing_data, json_file, indent=4)


def main():
    install_requirements()
    parser = argparse.ArgumentParser()
    parser.add_argument('date',
                        type=lambda d: is_date_valid(d) or parser.error("Invalid date. Please use YYYY-MM-DD format."))
    args = parser.parse_args()

    date = args.date.strftime('%Y-%m-%d')

    flag = True
    while flag:
        amount = get_amount()
        base_currency = get_currency_code()
        target_currency = get_currency_code()

        config = load_config()
        api_key = config['api_key']

        global get_exchange_rates_called
        exchange_rate = None
        if get_exchange_rates_called:
            exchange_rate = get_cached_exchange_rates(date, base_currency, target_currency)
        if exchange_rate is None:
            exchange_rate = get_exchange_rates(api_key, date, base_currency, target_currency)

        target_amount = round(float(exchange_rate) * float(amount), 2)

        print(f"{amount} {base_currency} is {target_amount} {target_currency}")

        save_to_output_file(date, amount, base_currency, target_amount, target_currency)


if __name__ == "__main__":
    main()
