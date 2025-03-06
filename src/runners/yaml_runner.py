class YAMLRunner(BaseRunner):
    def __init__(self, config_file="test_cases.yaml"):
        super().__init__(config_file)

    def load_test_cases(self):
        """Load test cases from a YAML file."""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            required_fields = ["name", "command", "args", "expected"]
            for case in config["test_cases"]:
                if not all(field in case for field in required_fields):
                    raise ValueError(f"Test case {case.get('name', 'unnamed')} is missing required fields")
                
                case["args"] = [
                    str(self.workspace / arg) if not arg.startswith("--") else arg
                    for arg in case["args"]
                ]
                self.test_cases.append(case)
                
            print(f"Successfully loaded {len(self.test_cases)} test cases")
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")