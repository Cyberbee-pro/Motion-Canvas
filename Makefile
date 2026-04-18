CXX      = g++
CXXFLAGS = -std=c++17 -O2 -Wall -fPIC -Icpp/include
TARGET   = engine.so

SRCS = cpp/src/Detectors.cpp \
       cpp/src/FreeFaceEngine.cpp \
       cpp/src/engine_api.cpp

all: $(TARGET)
	@echo ""
	@echo "✓ Built $(TARGET) — ready for Python"
	@echo ""

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) -shared -o $(TARGET) $(SRCS)

test: $(TARGET)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Running FreeFace Unit Tests"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	python3 test.py
	@echo ""

test-engine:
	@python3 test.py engine

test-camera:
	@python3 test.py camera

test-mediapipe:
	@python3 test.py mediapipe

test-gaze:
	@python3 test.py gaze

test-blink:
	@python3 test.py blink

test-voice:
	@python3 test.py voice

test-keyboard:
	@python3 test.py keyboard

test-os:
	@python3 test.py os

clean:
	rm -f $(TARGET)

.PHONY: all clean test test-engine test-camera test-mediapipe test-gaze test-blink test-voice test-keyboard test-os
