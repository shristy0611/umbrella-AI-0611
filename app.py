from quart import Quart, request, websocket, jsonify

app = Quart(__name__)

@app.route("/pdf-extract", methods=["POST"])
async def pdf_extract():
    # Simulate PDF extraction by returning dummy text and empty image list
    return jsonify({"text": "dummy extracted text", "images": []})

@app.route("/sentiment", methods=["POST"])
async def sentiment():
    # Simulate sentiment analysis by returning a dummy sentiment and score
    return jsonify({"sentiment": "happy", "score": 0.95})

@app.route("/rag-scrape", methods=["POST"])
async def rag_scrape():
    # Simulate RAG scraping by returning dummy results
    return jsonify({"results": ["dummy result 1", "dummy result 2"]})

@app.websocket("/chat")
async def chat():
    # Simulate chat response by waiting for a message and then sending a dummy response
    data = await websocket.receive()
    await websocket.send('{"response": "dummy chat response"}')

if __name__ == "__main__":
    # Run the app on port 8000
    app.run(host="0.0.0.0", port=8000)
