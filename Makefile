PYTHON ?= python3
SRC := src

.PHONY: all install spells talents wowhead excel clean help

all: spells talents wowhead excel

install:
	$(PYTHON) -m pip install -r requirements.txt

spells:
	$(PYTHON) $(SRC)/cleanse_spells.py

talents:
	$(PYTHON) $(SRC)/cleanse_talents.py

wowhead:
	$(PYTHON) $(SRC)/fetch_wowhead.py

excel:
	$(PYTHON) $(SRC)/build_excel.py

clean:
	rm -rf data/clean/*.json cache/wowhead_cache.json runs/*

help:
	@echo "用法:"
	@echo "  make install   安装依赖"
	@echo "  make all       跑完整流程 (推荐)"
	@echo "  make spells    只清洗施法次数 HTML"
	@echo "  make talents   只清洗天赋树 HTML"
	@echo "  make wowhead   只抓 Wowhead 描述"
	@echo "  make excel     只生成 Excel"
	@echo "  make clean     清空中间产物与归档"
