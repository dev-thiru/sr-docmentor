#!/bin/bash

/bin/ollama serve &
pid=$!

sleep 5

echo "Pulling model...."
ollama pull llama3.1:8b-instruct-q5_K_M
echo "Done!"

wait $pid