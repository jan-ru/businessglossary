SRC = $(wildcard ./*.ipynb)

all: businessglossary docs

businessglossary: $(SRC)
	nbdev_export
	touch businessglossary

sync:
	nbdev_update

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_docs
	touch docs

test:
	nbdev_test

release: pypi
	nbdev_bump_version

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python -m build

clean:
	rm -rf dist
