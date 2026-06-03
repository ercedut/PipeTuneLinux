CC ?= gcc
CFLAGS ?= -O2 -fPIC -Wall -Wextra -Werror
PKG_CONFIG ?= pkg-config
LV2_CFLAGS := $(shell $(PKG_CONFIG) --cflags lv2 2>/dev/null)
LDFLAGS ?= -shared
LDLIBS ?= -lm

TARGET = pipetune_safeguard.so
OBJECT = pipetune_safeguard.o
SOURCE = pipetune_safeguard.c

.PHONY: all check check-deps clean install

all: check-deps $(TARGET)

check-deps:
	@command -v $(PKG_CONFIG) >/dev/null 2>&1 || { echo "pkg-config is required to build the local LV2 plugin."; exit 1; }
	@$(PKG_CONFIG) --exists lv2 || { echo "LV2 development headers are missing. On Fedora, install: gcc make lv2-devel"; exit 1; }

$(OBJECT): $(SOURCE)
	$(CC) $(CFLAGS) $(LV2_CFLAGS) -c -o $@ $<

$(TARGET): $(OBJECT)
	$(CC) $(LDFLAGS) -o $@ $< $(LDLIBS)

check: all
	@test -f $(TARGET)

clean:
	rm -f $(TARGET) $(OBJECT)

install:
	@echo "Global install is intentionally unsupported. Use local build artifacts only."
	@exit 1
