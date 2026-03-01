# python swagger_to_excel.py

import pandas as pd
import requests
from datetime import datetime

def swagger_to_excel(swagger_url, output_file):
    """Convert Swagger OpenAPI spec to Excel file."""

    try:
        # Fetch OpenAPI spec
        print(f"Fetching OpenAPI spec from {swagger_url}...")
        response = requests.get(swagger_url)
        response.raise_for_status()
        spec = response.json()

        # Parse API information
        apis = []

        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():

                # Extract parameter info
                parameters = []
                if 'parameters' in details:
                    for param in details['parameters']:
                        param_info = f"{param.get('name', '')} ({param.get('in', '')}) - {param.get('description', '')}"
                        parameters.append(param_info)

                # Extract request body info
                request_body = ""
                if 'requestBody' in details:
                    content = details['requestBody'].get('content', {})
                    for content_type, schema_info in content.items():
                        request_body = f"{content_type}"
                        break

                # Extract response info
                responses = []
                if 'responses' in details:
                    for code, resp_info in details['responses'].items():
                        desc = resp_info.get('description', '')
                        responses.append(f"{code}: {desc}")

                # Extract tag info
                tags = ', '.join(details.get('tags', []))
                
                apis.append({
                    'Path': path,
                    'Method': method.upper(),
                    'Summary': details.get('summary', ''),
                    'Description': details.get('description', ''),
                    'Tags': tags,
                    'Parameters': '; '.join(parameters) if parameters else '',
                    'Request Body': request_body,
                    'Responses': '; '.join(responses) if responses else '',
                    'Deprecated': details.get('deprecated', False)
                })
        
        df = pd.DataFrame(apis)

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All APIs', index=False)

            for tag in df['Tags'].unique():
                if tag:
                    tag_df = df[df['Tags'].str.contains(tag, na=False)]
                    safe_tag_name = tag.replace('/', '_')[:30]  # Excel sheet name limit
                    tag_df.to_excel(writer, sheet_name=safe_tag_name, index=False)


            metadata = {
                'Info': ['API Title', 'Version', 'Description', 'Generated At'],
                'Value': [
                    spec.get('info', {}).get('title', 'N/A'),
                    spec.get('info', {}).get('version', 'N/A'), 
                    spec.get('info', {}).get('description', 'N/A'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        print(f"Excel file created: {output_file}")
        print(f"Total APIs: {len(apis)}")
        print(f"Tags found: {', '.join(df['Tags'].unique())}")
        
    except requests.RequestException as e:
        print(f"Error fetching OpenAPI spec: {e}")
    except Exception as e:
        print(f"Error converting to Excel: {e}")

if __name__ == "__main__":
    SWAGGER_URL = "http://localhost:8000/openapi.json"
    OUTPUT_FILE = "bizlenz_api_documentation.xlsx"
    swagger_to_excel(SWAGGER_URL, OUTPUT_FILE)
