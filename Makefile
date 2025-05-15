# These are `make` commands that are useful for development.
# 
# Before running these `make` commands, make sure to set
# DBNAME, INDEXED_REPO_PATH, MODULE_NAMES, CHROMA_PATH env vars.
# 
# For example, you can have the following in your ~/.bashrc:
# 
# export DBNAME=magic
# export INDEXED_REPO_PATH=/home/lakesare/Desktop/magic
# export MODULE_NAMES=Magic
# export CHROMA_PATH=chroma

check_env:
	@test -n "$(DBNAME)"            || (echo "Please set DBNAME in your .env"            && exit 1)
	@test -n "$(INDEXED_REPO_PATH)" || (echo "Please set INDEXED_REPO_PATH in your .env" && exit 1)
	@test -n "$(MODULE_NAMES)"      || (echo "Please set MODULE_NAMES in your .env"      && exit 1)
	@test -n "$(CHROMA_PATH)"       || (echo "Please set MODULE_NAMES in your .env"      && exit 1)

reset:
	make check_env
	@echo "\n__________________Dropping and recreating PostgreSQL database '$(DBNAME)'..."
	-dropdb $(DBNAME)
	createdb $(DBNAME)
	@echo "\n__________________Clearing ChromaDB files..."
	rm -rf $(CHROMA_PATH)
	@echo "\n__________________Clearing build outputs..."
	cd $(INDEXED_REPO_PATH) && lake clean && lake build
	cd $(INDEXED_REPO_PATH) && rm -rf ./.jixia
	@echo "\n__________________Creating database schema..."
	python3 -m database schema
	@echo "\n__________________DONE."

jixia:
	make reset
	@echo "\n__________________Parsing the project using jixia..."
	python3 -m database jixia $(INDEXED_REPO_PATH) $(MODULE_NAMES)

informal:
	make reset
	make jixia
	@echo "\n__________________Creating informal descriptions using DeepSeek..."
	python3 -m database informal

index:
	make reset
	make informal
	@echo "\n__________________Creating embeddings using Mistral..."
	python3 -m database vector-db
