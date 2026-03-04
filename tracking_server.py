from flask import Flask, send_file, request, jsonify, make_response
from io import BytesIO
from PIL import Image
import json
from datetime import datetime
import os

app = Flask(__name__)

# Use environment variable for data file location (Render persistent storage)
DATA_DIR = os.environ.get('DATA_DIR', '.')
TRACKING_FILE = os.path.join(DATA_DIR, 'email_opens.json')

def load_tracking_data():
    """Load tracking data from JSON file"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️  Corrupted tracking file, creating new one")
            return {}
    return {}

def save_tracking_data(data):
    """Save tracking data to JSON file"""
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving tracking data: {e}")

@app.route('/')
def home():
    """Home page with API documentation"""
    return jsonify({
        'service': 'Email Tracking Server',
        'status': 'running',
        'endpoints': {
            '/track/<tracking_id>.png': 'Tracking pixel endpoint',
            '/stats/<tracking_id>': 'Get stats for specific email',
            '/stats': 'Get all tracking stats',
            '/health': 'Health check endpoint'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/track/<tracking_id>.png')
def track_pixel(tracking_id):
    """
    Tracking pixel endpoint
    Returns 1x1 transparent PNG and logs the email open
    """
    # Log the request
    print(f"📧 Tracking pixel requested: {tracking_id}")
    print(f"   From IP: {request.remote_addr}")
    print(f"   User-Agent: {request.user_agent.string[:100]}")
    print(f"   Referer: {request.headers.get('Referer', 'N/A')}")
    
    # Load current tracking data
    data = load_tracking_data()
    
    # Record the open
    if tracking_id not in data:
        data[tracking_id] = {
            'first_opened': datetime.now().isoformat(),
            'open_count': 1,
            'opens': []
        }
        print(f"   ✅ FIRST OPEN RECORDED!")
    else:
        data[tracking_id]['open_count'] += 1
        print(f"   📊 Open count: {data[tracking_id]['open_count']}")
    
    # Log this specific open event
    data[tracking_id]['opens'].append({
        'timestamp': datetime.now().isoformat(),
        'ip': request.remote_addr,
        'user_agent': request.user_agent.string,
        'referer': request.headers.get('Referer', 'unknown')
    })
    
    # Save updated data
    save_tracking_data(data)
    
    # Create 1x1 transparent PNG
    img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    # Create response with proper headers
    response = make_response(send_file(
        img_io, 
        mimetype='image/png',
        as_attachment=False
    ))
    
    # Anti-caching headers (important for accurate tracking)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    return response

@app.route('/stats/<tracking_id>')
def get_stats(tracking_id):
    """Get tracking stats for a specific email"""
    data = load_tracking_data()
    
    if tracking_id in data:
        return jsonify(data[tracking_id]), 200
    
    return jsonify({
        'error': 'Tracking ID not found',
        'tracking_id': tracking_id
    }), 404

@app.route('/stats')
def get_all_stats():
    """Get all tracking stats"""
    data = load_tracking_data()
    
    # Add summary
    total_emails = len(data)
    total_opens = sum(email.get('open_count', 0) for email in data.values())
    opened_emails = sum(1 for email in data.values() if email.get('open_count', 0) > 0)
    
    return jsonify({
        'summary': {
            'total_tracked_emails': total_emails,
            'total_opens': total_opens,
            'emails_opened': opened_emails,
            'open_rate': f"{(opened_emails/total_emails*100):.1f}%" if total_emails > 0 else "0%"
        },
        'emails': data
    }), 200

@app.route('/delete/<tracking_id>', methods=['DELETE', 'POST'])
def delete_tracking(tracking_id):
    """Delete tracking data for a specific email (optional endpoint)"""
    data = load_tracking_data()
    
    if tracking_id in data:
        del data[tracking_id]
        save_tracking_data(data)
        return jsonify({
            'success': True,
            'message': f'Tracking data for {tracking_id} deleted'
        }), 200
    
    return jsonify({
        'error': 'Tracking ID not found'
    }), 404

if __name__ == '__main__':
    # Print startup info
    print("=" * 70)
    print("🚀 EMAIL TRACKING SERVER STARTING")
    print("=" * 70)
    print(f"Data file: {TRACKING_FILE}")
    print("Endpoints:")
    print("  GET  /                    - API documentation")
    print("  GET  /health              - Health check")
    print("  GET  /track/<id>.png      - Tracking pixel")
    print("  GET  /stats/<id>          - Email stats")
    print("  GET  /stats               - All stats")
    print("=" * 70)
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
