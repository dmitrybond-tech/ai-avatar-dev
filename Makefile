RUN_MINIAPP := ./scripts/run-miniapp.sh
SERVICES ?=
ARGS ?=

.PHONY: pull up down logs ps config

pull:
	$(RUN_MINIAPP) pull $(SERVICES)

up:
	$(RUN_MINIAPP) up $(ARGS) $(SERVICES)

down:
	$(RUN_MINIAPP) down $(ARGS) $(SERVICES)

logs:
	$(RUN_MINIAPP) logs $(ARGS) $(SERVICES)

ps:
	$(RUN_MINIAPP) ps $(ARGS) $(SERVICES)

config:
	$(RUN_MINIAPP) config

