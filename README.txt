# FitNutrition project files

## Files
- `FitNutrition.ipynb`: notebook with data validation, nutrient calculations, comparisons, SQLite example, charts, testing plan and limitations.
- `app.py`: interactive Streamlit app with meal logging, dashboard, food comparison, targets, custom foods and history analytics.
- `food_data.csv`: small illustrative food dataset.
- `requirements.txt`: Python dependencies.
- `FitNutrition_Project_Report.pdf`: draft project report. Add real screenshots and verified test outcomes after running the app.

## Run on Windows
1. Extract this folder.
2. Open PowerShell in the folder.
3. (Optional but recommended) Create a virtual environment:
   `py -m venv .venv`
   `.\.venv\Scripts\Activate.ps1`
4. Install dependencies:
   `py -m pip install -r requirements.txt`
5. Start the app:
   `py -m streamlit run app.py`
6. Open the local address printed in the terminal.
7. Open `FitNutrition.ipynb` in Jupyter Notebook and run cells from top to bottom.

## Notes
- The CSV values are approximate illustrative values for demonstrating software functionality. Verify nutrition values and document sources before claiming they are authoritative.
- The report is a draft and should be updated with your own screenshots, actual test results, and any institution-specific cover-page details.
- The app stores data in `nutrition.db` when run. The notebook uses `nutrition_demo.db`.
