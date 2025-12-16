from flask import Flask, jsonify, request

app = Flask(__name__)

# Sample data (replace with your actual data)
activities = [
    {"id": 1, "name": "Morning Meeting", "date": "2023-10-01"},
    {"id": 2, "name": "Project Review", "date": "2023-10-01"}
]

@app.route('/activity', methods=['GET'])
def get_activities():
    return jsonify({
        "success": True,
        "data": activities
    })

if __name__ == '__main__':
    app.run(host='localhost', port=5000)  # Run on port 5000