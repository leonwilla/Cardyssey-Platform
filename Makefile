.PHONY: contract generate verify

contract:
	python3 scripts/write-contract.py
	./scripts/contract-check.sh

generate:
	./scripts/generate-clients.sh

verify:
	./scripts/verify-contract.sh
