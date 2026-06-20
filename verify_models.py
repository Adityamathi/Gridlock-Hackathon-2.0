from pathlib import Path
import joblib

MODELS_DIR = Path('outputs/models')

# Check all 3 models exist
models = ['severity_model.joblib', 'closure_model.joblib', 'duration_model.joblib']

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
    print('\n✓✓✓ Step 4 PASSED - All models load correctly!')
else:
    print('\n✗✗✗ Step 4 FAILED - Some models missing')