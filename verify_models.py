from pathlib import Path
import joblib

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "outputs" / "models"

# Check all models exist (3 main + 3 resource)
models = [
    'severity_model.joblib',
    'closure_model.joblib',
    'duration_model.joblib',
    'officers_model.joblib',
    'barricades_model.joblib',
    'patrols_model.joblib',
]

all_ok = True
for model_name in models:
    path = MODELS_DIR / model_name
    if path.exists():
        model = joblib.load(path)
        print(f'✓ {model_name} loaded successfully')
    else:
        print(f'✗ {model_name} NOT FOUND')
        all_ok = False

if all_ok:
    print(f'\n✓✓✓ All {len(models)} models load correctly!')
else:
    print(f'\n✗✗✗ Some models missing')