CC = gcc
CFLAGS = -fPIC -fno-stack-protector -Wall
LDFLAGS = -x --shared
LIBS = -lpam
TARGET = src/pam_gesture.so
OBJ = src/pam_gesture.o

.PHONY: all clean dev-install install

all: $(TARGET)

$(OBJ): src/pam_gesture.c
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJ)
	ld $(LDFLAGS) -o $@ $(OBJ) $(LIBS)

clean:
	rm -f $(OBJ) $(TARGET)

# JUST FOR DEVELOPMENT PURPOSES, NOT FOR PRODUCTION USE
dev-install: $(TARGET)
	sudo cp $(TARGET) /usr/lib/security/
	sudo chmod 755 /usr/lib/security/pam_gesture.so
	sudo chown root:root /usr/lib/security/pam_gesture.so

# Miantain compatibility
install:
	@echo "Use 'make dev-install' (only development). For real installation use PKGBUILD/makepkg."
	@false