import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import re


def get_tc_prefix(tc_name: str) -> str:
    """Vrátí prvních dvě čísla z TC, např. 'TC.01.01' → '01.01'"""
    match = re.match(r"TC\.(\d+\.\d+)", tc_name)
    return match.group(1) if match else ""


def get_tk_prefix(tk_name: str) -> str:
    """Vrátí prvních dvě čísla z TK, např. 'TK.01.01.04::...' → '01.01'"""
    match = re.match(r"TK\.(\d+\.\d+)", tk_name)
    return match.group(1) if match else ""


def load_test_steps(round_path: str):
    """
    Načte všechny TK přímo z test_case_run_log_report.xml.
    Vrátí dict: {tc_prefix: [list of TK dict]}
    """
    steps_mapping = {}
    log_file = os.path.join(round_path, "test_case_run_log_report.xml")
    if not os.path.exists(log_file):
        return steps_mapping

    try:
        tree = ET.parse(log_file)
        root = tree.getroot()
        ns = {'con': 'http://eviware.com/soapui/config'}

        # Procházíme přímo všechny TK
        for step in root.findall(".//con:testCaseRunLogTestStep", ns):
            tk_name = step.attrib.get("name", "")
            # Prefix prvních dvou čísel z TK: "01.01" z "TK.01.01.04::..."
            tk_prefix = ".".join(tk_name.split("::")[0].split(".")[1:3])

            tk_data = {
                "name": tk_name,
                "status": step.attrib.get("status", ""),
                "timeTaken": int(step.attrib.get("timeTaken", "0")),
                "httpMethod": step.attrib.get("httpMethod", ""),
                "endpoint": step.attrib.get("endpoint", ""),
                "timestamp": step.attrib.get("timestamp", ""),
                "httpStatus": step.attrib.get("httpStatus", ""),
            }

            if tk_prefix not in steps_mapping:
                steps_mapping[tk_prefix] = []
            steps_mapping[tk_prefix].append(tk_data)

    except Exception as e:
        print(f"Chyba při načítání TK z {log_file}: {e}")

    return steps_mapping


def process_test_suites(rounds_dir: str, output_dir: str):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for round_folder in os.listdir(rounds_dir):
        round_path = os.path.join(rounds_dir, round_folder)
        if os.path.isdir(round_path) and round_folder.startswith("round_"):
            round_number = int(round_folder.split("_")[1]) + 1

            # Načti TK pro dané kolo
            test_steps_mapping = load_test_steps(round_path)

            for file_name in os.listdir(round_path):
                if file_name.endswith('.xml') and file_name != "test_case_run_log_report.xml":
                    xml_file_path = os.path.join(round_path, file_name)
                    json_file_path = os.path.join(output_dir, f"{file_name}_round{round_number}.json")
                    if os.path.exists(json_file_path):
                        print(f"Skipping {file_name}_round{round_number}.json")
                        continue
                    try:
                        tree = ET.parse(xml_file_path)
                        root = tree.getroot()

                        testsuite = root.attrib
                        test_cases = root.findall("testcase")

                        json_data = []
                        for testcase in test_cases:
                            tc_name = testcase.attrib.get("name", "")
                            failure = testcase.find("failure")
                            message = ""
                            if failure is not None and failure.text:
                                match = re.search(r"<pre>(.*?)</pre>", failure.text, re.DOTALL)
                                if match:
                                    message = match.group(1).strip()

                            # připoj TK podle prefixu
                            tc_prefix = get_tc_prefix(tc_name)
                            tk_list = test_steps_mapping.get(tc_prefix, [])

                            json_data.append({
                                "round": round_number,
                                "idTS": testsuite.get("name", "").split("::")[0].split("PTE_semestralni_prace.")[1],
                                "nameTS": testsuite.get("name", "").split("::")[1],
                                "idTC": tc_name.split("::")[0],
                                "nameTC": tc_name.split("::")[1],
                                "status": "FAILED" if failure is not None else "PASSED",
                                "@timestamp": tk_list[0]["timestamp"] if tk_list else "",
                                "totalTime": int(float(testcase.attrib.get("time", "0")) * 1000),
                                "httpMethod": tk_list[0]["httpMethod"] if tk_list else "",
                                "message": message,
                                "httpStatus": tk_list[0]["httpStatus"] if tk_list else "",
                            })

                        with open(json_file_path, 'w', encoding='utf-8') as json_file:
                            json.dump(json_data, json_file, indent=4, ensure_ascii=False)

                        print(f"Soubor {file_name} byl úspěšně převeden do JSON.")
                    except Exception as e:
                        print(f"Chyba při zpracování souboru {file_name}: {e}")
