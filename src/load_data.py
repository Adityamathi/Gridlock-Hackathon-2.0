import pandas as pd
from config import DATA_FILE

def load_dataset():
    df = pd.read_csv(DATA_FILE, low_memory=False)

    for col in ["start_datetime", "end_datetime", "closed_datetime", "created_date", "modified_datetime"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")

    return df

if __name__ == "__main__":
    df = load_dataset()
    print("Shape:", df.shape)
    print("Columns:", len(df.columns))
    print("Sample columns:", df.columns.tolist()[:10])