# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
.PHONY: install run test catalog docker
install: ; pip install -r requirements.txt pytest
run:     ; uvicorn omnis.api:app --reload --port 8080
test:    ; python -m pytest -q
catalog: ; PYTHONPATH=. python -m omnis.inventory > catalog.json
docker:  ; docker build -f Dockerfile -t omnis ..
