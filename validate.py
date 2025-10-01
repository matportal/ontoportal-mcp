from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename
import yaml

def validate_spec(filepath):
    """
    Validates an OpenAPI specification file.
    """
    try:
        spec_dict, _ = read_from_filename(filepath)
        validate(spec_dict)
        print("Validation successful!")
    except Exception as e:
        print(f"Validation failed: {e}")

if __name__ == "__main__":
    validate_spec('openapi.yaml')
