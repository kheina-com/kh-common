.PHONY: test
test:
	python3 -m pip install --upgrade pip
	python3 -m pip install pipenv
	pipenv --python 3.7
	pipenv run find . -name 'requirements*.txt' -exec python -m pip install -r {} \;
	pipenv lock
	pipenv run pytest
	pipenv --rm
