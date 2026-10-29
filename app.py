import sqlite3
from pathlib import Path
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "nutrition.db"
CSV_PATH = APP_DIR / "food_data.csv"

st.set_page_config(page_title="FitNutrition", page_icon="🥗", layout="wide")

def connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with connect_db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS foods (
            food_id INTEGER PRIMARY KEY, food_name TEXT UNIQUE, category TEXT,
            serving_g REAL, calories_kcal_per_100g REAL, protein_g_per_100g REAL,
            carbs_g_per_100g REAL, fat_g_per_100g REAL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS meals (
            meal_id INTEGER PRIMARY KEY AUTOINCREMENT, meal_date TEXT, meal_type TEXT,
            food_id INTEGER, food_name TEXT, quantity_g REAL, calories REAL,
            protein_g REAL, carbs_g REAL, fat_g REAL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS targets (
            target_id INTEGER PRIMARY KEY CHECK(target_id=1), calories REAL, protein_g REAL,
            carbs_g REAL, fat_g REAL)""")
        count = con.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
        if count == 0 and CSV_PATH.exists():
            df = pd.read_csv(CSV_PATH)
            df.to_sql("foods", con, if_exists="append", index=False)
        target = con.execute("SELECT COUNT(*) FROM targets").fetchone()[0]
        if target == 0:
            con.execute("INSERT INTO targets VALUES (1, 2000, 100, 250, 65)")

def get_foods():
    with connect_db() as con:
        return pd.read_sql_query("SELECT * FROM foods ORDER BY food_name", con)

def get_meals(start=None, end=None):
    query = "SELECT * FROM meals"
    params = []
    if start and end:
        query += " WHERE meal_date BETWEEN ? AND ?"
        params = [str(start), str(end)]
    query += " ORDER BY meal_date DESC, meal_id DESC"
    with connect_db() as con:
        return pd.read_sql_query(query, con, params=params)

def get_targets():
    with connect_db() as con:
        row = con.execute("SELECT calories, protein_g, carbs_g, fat_g FROM targets WHERE target_id=1").fetchone()
    return dict(zip(["calories","protein_g","carbs_g","fat_g"], row))

def calc_nutrients(food, quantity_g):
    factor = float(quantity_g) / 100
    return {
        "calories": round(food["calories_kcal_per_100g"] * factor, 1),
        "protein_g": round(food["protein_g_per_100g"] * factor, 1),
        "carbs_g": round(food["carbs_g_per_100g"] * factor, 1),
        "fat_g": round(food["fat_g_per_100g"] * factor, 1),
    }

init_db()
st.title("🥗 FitNutrition")
st.caption("Personalized nutrition tracking and dietary analytics — educational prototype using sample food data.")

foods_df = get_foods()
tabs = st.tabs(["Dashboard", "Log a Meal", "Food Comparison", "Targets & Food Database", "Meal History"])

with tabs[0]:
    st.subheader("Daily nutrition overview")
    chosen_date = st.date_input("Choose date", value=date.today(), key="dashboard_date")
    all_meals = get_meals(chosen_date, chosen_date)
    targets = get_targets()
    totals = {k: float(all_meals[k].sum()) if not all_meals.empty else 0.0
              for k in ["calories","protein_g","carbs_g","fat_g"]}
    cols = st.columns(4)
    for col, label, key, unit in zip(cols, ["Calories","Protein","Carbohydrates","Fat"],
                                     ["calories","protein_g","carbs_g","fat_g"], ["kcal","g","g","g"]):
        col.metric(label, f"{totals[key]:.1f} {unit}", f"Target {targets[key]:g} {unit}")
        col.progress(min(totals[key] / targets[key], 1.0) if targets[key] > 0 else 0.0)
    if all_meals.empty:
        st.info("No meals logged for this date yet. Open 'Log a Meal' to add your first entry.")
    else:
        chart_df = pd.DataFrame({"Nutrient":["Protein (g)","Carbohydrates (g)","Fat (g)"],
                                 "Amount":[totals["protein_g"],totals["carbs_g"],totals["fat_g"]]})
        st.plotly_chart(px.bar(chart_df, x="Nutrient", y="Amount", title="Macronutrient intake"), use_container_width=True)
        st.dataframe(all_meals[["meal_type","food_name","quantity_g","calories","protein_g","carbs_g","fat_g"]], use_container_width=True)
    st.caption("Targets are configurable estimates, not medical advice.")

with tabs[1]:
    st.subheader("Log a meal")
    if foods_df.empty:
        st.warning("No foods available. Add foods in the Targets & Food Database tab.")
    else:
        with st.form("meal_form"):
            meal_date = st.date_input("Meal date", value=date.today())
            meal_type = st.selectbox("Meal type", ["Breakfast","Lunch","Dinner","Snack"])
            food_name = st.selectbox("Food", foods_df["food_name"].tolist())
            quantity_g = st.number_input("Quantity in grams", min_value=1.0, max_value=3000.0, value=100.0, step=10.0)
            submitted = st.form_submit_button("Save meal")
        if submitted:
            food = foods_df.loc[foods_df["food_name"] == food_name].iloc[0]
            nutrients = calc_nutrients(food, quantity_g)
            with connect_db() as con:
                con.execute("""INSERT INTO meals
                    (meal_date,meal_type,food_id,food_name,quantity_g,calories,protein_g,carbs_g,fat_g)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (str(meal_date),meal_type,int(food["food_id"]),food_name,float(quantity_g),
                     nutrients["calories"],nutrients["protein_g"],nutrients["carbs_g"],nutrients["fat_g"]))
            st.success(f"Saved {quantity_g:g} g of {food_name}. Estimated energy: {nutrients['calories']} kcal.")
            st.rerun()

with tabs[2]:
    st.subheader("Compare foods")
    selected = st.multiselect("Choose 2–4 foods to compare", foods_df["food_name"].tolist(),
                              default=foods_df["food_name"].head(3).tolist())
    basis = st.radio("Compare by", ["Per 100 g", "Typical serving"], horizontal=True)
    if selected:
        comp = foods_df[foods_df["food_name"].isin(selected)].copy()
        if basis == "Typical serving":
            factor = comp["serving_g"] / 100
            comp["Calories (kcal)"] = comp["calories_kcal_per_100g"] * factor
            comp["Protein (g)"] = comp["protein_g_per_100g"] * factor
            comp["Carbs (g)"] = comp["carbs_g_per_100g"] * factor
            comp["Fat (g)"] = comp["fat_g_per_100g"] * factor
            comp["Basis"] = comp["serving_g"].astype(str) + " g serving"
        else:
            comp["Calories (kcal)"] = comp["calories_kcal_per_100g"]
            comp["Protein (g)"] = comp["protein_g_per_100g"]
            comp["Carbs (g)"] = comp["carbs_g_per_100g"]
            comp["Fat (g)"] = comp["fat_g_per_100g"]
            comp["Basis"] = "per 100 g"
        st.dataframe(comp[["food_name","Basis","Calories (kcal)","Protein (g)","Carbs (g)","Fat (g)"]].round(1),
                     use_container_width=True)
        st.plotly_chart(px.bar(comp, x="food_name", y="Protein (g)", title=f"Protein comparison — {basis}"),
                        use_container_width=True)

with tabs[3]:
    st.subheader("Nutrition targets")
    targets = get_targets()
    with st.form("target_form"):
        c1,c2,c3,c4 = st.columns(4)
        calories = c1.number_input("Calories (kcal/day)", min_value=500.0, max_value=6000.0, value=float(targets["calories"]), step=50.0)
        protein = c2.number_input("Protein (g/day)", min_value=10.0, max_value=350.0, value=float(targets["protein_g"]), step=5.0)
        carbs = c3.number_input("Carbohydrates (g/day)", min_value=10.0, max_value=800.0, value=float(targets["carbs_g"]), step=10.0)
        fat = c4.number_input("Fat (g/day)", min_value=5.0, max_value=250.0, value=float(targets["fat_g"]), step=5.0)
        saved = st.form_submit_button("Save targets")
    if saved:
        with connect_db() as con:
            con.execute("UPDATE targets SET calories=?, protein_g=?, carbs_g=?, fat_g=? WHERE target_id=1",
                        (calories,protein,carbs,fat))
        st.success("Targets updated.")
        st.rerun()
    st.divider()
    st.subheader("Food database")
    st.dataframe(foods_df, use_container_width=True)
    with st.expander("Add a custom food"):
        with st.form("custom_food"):
            name = st.text_input("Food name")
            category = st.selectbox("Category", ["Protein","Carbohydrate","Dairy","Fruit","Vegetable","Legume","Other"])
            serving = st.number_input("Typical serving (g)", min_value=1.0, value=100.0)
            cal = st.number_input("Calories per 100 g", min_value=0.0, value=100.0)
            pro = st.number_input("Protein (g per 100 g)", min_value=0.0, value=5.0)
            carb = st.number_input("Carbohydrates (g per 100 g)", min_value=0.0, value=10.0)
            fatv = st.number_input("Fat (g per 100 g)", min_value=0.0, value=2.0)
            add = st.form_submit_button("Add food")
        if add:
            if not name.strip():
                st.error("Enter a food name.")
            else:
                try:
                    with connect_db() as con:
                        next_id = con.execute("SELECT COALESCE(MAX(food_id),0)+1 FROM foods").fetchone()[0]
                        con.execute("INSERT INTO foods VALUES (?,?,?,?,?,?,?,?)",
                                    (next_id,name.strip(),category,serving,cal,pro,carb,fatv))
                    st.success("Food added.")
                    st.rerun()
                except Exception:
                    st.error("That food may already exist. Try a different name.")

with tabs[4]:
    st.subheader("Meal history and weekly analytics")
    end_date = st.date_input("History end date", value=date.today(), key="history_end")
    start_date = st.date_input("History start date", value=end_date-timedelta(days=6), key="history_start")
    history = get_meals(start_date, end_date)
    if history.empty:
        st.info("No meals recorded in this date range.")
    else:
        st.dataframe(history, use_container_width=True)
        daily = history.groupby("meal_date", as_index=False).agg(
            Calories=("calories","sum"), Protein_g=("protein_g","sum"),
            Carbs_g=("carbs_g","sum"), Fat_g=("fat_g","sum"))
        st.plotly_chart(px.line(daily, x="meal_date", y="Protein_g", markers=True,
                                title="Daily protein intake over time"), use_container_width=True)
        st.plotly_chart(px.bar(daily, x="meal_date", y="Calories", title="Daily calorie intake"),
                        use_container_width=True)
        target = get_targets()["protein_g"]
        below = daily[daily["Protein_g"] < target]
        st.write(f"Days with recorded protein below target: **{len(below)}** out of {len(daily)} days with entries.")
        st.caption("Days with no logged meals are not counted as zero-intake days.")
