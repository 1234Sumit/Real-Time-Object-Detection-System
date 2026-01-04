@app.route('/stop_detection')
def stop_detection():
    global detection_active
    detection_active = False
    return 'Detection stopped'