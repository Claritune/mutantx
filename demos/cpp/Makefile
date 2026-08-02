CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra

# macOS: if standard C++ headers are missing, add SDK include path
SYSROOT := $(shell xcrun --show-sdk-path 2>/dev/null)
ifneq ($(wildcard $(SYSROOT)/usr/include/c++/v1/stdexcept),)
  CXXFLAGS += -isystem $(SYSROOT)/usr/include/c++/v1
endif

TARGET = test_runner

SRCS = calculator.cpp test_calculator.cpp
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp calculator.h
	$(CXX) $(CXXFLAGS) -c $< -o $@

test: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all test clean
