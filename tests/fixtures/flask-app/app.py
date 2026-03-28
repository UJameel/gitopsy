"""Simple Flask application for testing."""

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/users", methods=["GET", "POST"])
def users():
    """List or create users."""
    if request.method == "GET":
        # TODO: implement pagination
        return jsonify({"users": []})
    # Create user
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    return jsonify({"created": True}), 201


@app.route("/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
def user_detail(user_id: int):
    """Get, update, or delete a specific user."""
    # FIXME: add proper error handling
    if request.method == "GET":
        return jsonify({"id": user_id})
    if request.method == "PUT":
        return jsonify({"id": user_id, "updated": True})
    return jsonify({"deleted": True})


if __name__ == "__main__":
    app.run(debug=True)
