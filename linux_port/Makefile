CXX      = g++
CXXFLAGS = -std=c++17 -O2 -Wall -fPIC -Icpp/include
TARGET   = engine.so

ifneq ("$(wildcard venv/bin/python3)","")
PYTHON := $(abspath venv/bin/python3)
else ifneq ("$(wildcard ../venv/bin/python3)","")
PYTHON := $(abspath ../venv/bin/python3)
else
PYTHON := python3
endif

SRCS = cpp/src/Detectors.cpp \
       cpp/src/FreeFaceEngine.cpp \
       cpp/src/engine_api.cpp

all: $(TARGET)
	@echo ""
	@echo "Built $(TARGET) - ready for Python"
	@echo ""

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) -shared -o $(TARGET) $(SRCS)

test: $(TARGET)
	@echo ""
	@echo "Running FreeFace Unit Tests"
	@echo ""
	"$(PYTHON)" test.py
	@echo ""

test-engine:
	@"$(PYTHON)" test.py engine

test-camera:
	@"$(PYTHON)" test.py camera

test-mediapipe:
	@"$(PYTHON)" test.py mediapipe

test-gaze:
	@"$(PYTHON)" test.py gaze

test-blink:
	@"$(PYTHON)" test.py blink

test-voice:
	@"$(PYTHON)" test.py voice

test-keyboard:
	@"$(PYTHON)" test.py keyboard

test-os:
	@"$(PYTHON)" test.py os

clean:
	rm -f $(TARGET)

.PHONY: all clean test test-engine test-camera test-mediapipe test-gaze test-blink test-voice test-keyboard test-os
