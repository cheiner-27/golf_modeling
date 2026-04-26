# golf_modeling
Machine learning project for predicting professional golf results

## Pipeline

```
python src/extract.py            # pull raw DataGolf API data → data/raw/
python src/fetch_weather.py      # pull weather for events    → data/raw/weather/
python src/process.py            # build players/courses/events/rounds + weather → data/processed/
python src/build_event_table.py  # aggregate to (event, player) training table   → data/processed/event_table.csv
```
