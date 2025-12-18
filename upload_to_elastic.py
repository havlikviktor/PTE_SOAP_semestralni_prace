import os
import json
from elasticsearch import Elasticsearch, exceptions
from dotenv import load_dotenv


class Elastic:
    def __init__(self):
        url = os.getenv("ELASTIC_API_URL")
        api_key = os.getenv("ELASTIC_API_TOKEN")
        self.els = Elasticsearch(
            hosts=[url],
            headers={"Authorization": f"ApiKey {api_key}"},
            verify_certs=True
        )

    def create_index(self, index_name: str, mapping: dict) -> None:
        try:
            if not self.els.indices.exists(index=index_name):
                self.els.indices.create(index=index_name, body=mapping)
                print(f"Index '{index_name}' vytvořen.")
            else:
                print(f"Index '{index_name}' již existuje.")
        except exceptions.ElasticsearchException as e:
            print(f"Chyba při vytváření indexu: {e}")

    def write_to_elastic_request(self, index: str, dict_data: dict) -> None:
        try:
            response = self.els.index(index=index, document=dict_data)
            if response.get('result') not in ('created', 'updated'):
                print(response)
        except exceptions.ElasticsearchException as e:
            print(f"Chyba při zápisu dokumentu: {e}")

    def write_jsonfile_to_elastic(self, index: str, json_file_name: str) -> None:
        with open(json_file_name, encoding='utf-8') as file:
            data = json.load(file)

        if not isinstance(data, list):
            print("JSON soubor musí být pole objektů!")
            return

        print(f"Nahrávám {len(data)} dokumentů do indexu '{index}'...")
        for i, doc in enumerate(data, start=1):
            self.write_to_elastic_request(index=index, dict_data=doc)
        print("Hotovo!")

    def write_directory_to_elastic(self, index: str, directory_path: str) -> None:
        if not os.path.isdir(directory_path):
            print(f"Cesta '{directory_path}' není platný adresář!")
            return

        json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
        if not json_files:
            print(f"V adresáři '{directory_path}' nebyly nalezeny žádné JSON soubory.")
            return

        if not self.els.indices.exists(index=index):
            print(f"Index '{index}' neexistuje. Vytvářím nový index s výchozím mapováním.")
            default_mapping = {
                "mappings": {
                    "properties": {
                        "round": {
                            "type": "integer"
                        },
                        "idTS": {
                            "type": "keyword"
                        },
                        "nameTS": {
                            "type": "keyword"
                        },
                        "idTC": {
                            "type": "keyword"
                        },
                        "nameTC": {
                            "type": "keyword"
                        },
                        "status": {
                            "type": "keyword"
                        },
                        "@timestamp": {
                            "type": "date",
                            "format": "yyyy-MM-dd HH:mm:ss"
                        },
                        "totalTime": {
                            "type": "integer"
                        },
                        "httpMethod": {
                            "type": "keyword"
                        },
                        "message": {
                            "type": "text"
                        },
                        "httpStatus": {
                            "type": "keyword"
                        }
                    }
                }
            }
            self.create_index(index, default_mapping)

        print(f"Nahrávám JSON soubory z adresáře '{directory_path}' do indexu '{index}'...")
        for file_name in json_files:
            file_path = os.path.join(directory_path, file_name)
            print(f"Zpracovávám soubor: {file_name}")
            self.write_jsonfile_to_elastic(index, file_path)
        print("Všechny soubory byly zpracovány.")
