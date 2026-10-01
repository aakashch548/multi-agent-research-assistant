.PHONY: install train predict app test

install:
	pip install -r requirements.txt
	python -c "import nltk; nltk.download('stopwords')"

train:
	python scripts/train.py

predict:
	python scripts/predict.py --text "Sample job posting text"

app:
	streamlit run app/streamlit_app.py

test:
	pytest
