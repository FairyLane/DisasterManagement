from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'disaster-management-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///disaster_management.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class DisasterReport(db.Model):
    __tablename__ = 'disaster_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    disaster_type = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_contact = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='pending')
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DisasterReport {self.id}: {self.disaster_type} at {self.location}>'

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Alert {self.id}: {self.title}>'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['GET', 'POST'])
def report_disaster():
    if request.method == 'POST':
        disaster_type = request.form.get('disaster_type')
        location = request.form.get('location')
        severity = request.form.get('severity')
        description = request.form.get('description')
        reporter_name = request.form.get('reporter_name')
        reporter_contact = request.form.get('reporter_contact')
        
        if all([disaster_type, location, severity, description, reporter_name, reporter_contact]):
            new_report = DisasterReport(
                disaster_type=disaster_type,
                location=location,
                severity=severity,
                description=description,
                reporter_name=reporter_name,
                reporter_contact=reporter_contact
            )
            db.session.add(new_report)
            db.session.commit()
            flash('Disaster report submitted successfully! Our team will review it shortly.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Please fill in all required fields.', 'danger')
    
    return render_template('report.html')

@app.route('/dashboard')
def dashboard():
    verified_reports = DisasterReport.query.filter_by(status='verified').order_by(DisasterReport.reported_at.desc()).all()
    return render_template('dashboard.html', reports=verified_reports)

@app.route('/admin')
def admin():
    all_reports = DisasterReport.query.order_by(DisasterReport.reported_at.desc()).all()
    return render_template('admin.html', reports=all_reports)

@app.route('/admin/update_status/<int:report_id>', methods=['POST'])
def update_status(report_id):
    report = DisasterReport.query.get_or_404(report_id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'verified', 'resolved']:
        report.status = new_status
        db.session.commit()
        flash(f'Report #{report_id} status updated to {new_status}.', 'success')
    else:
        flash('Invalid status value.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    report = DisasterReport.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash(f'Report #{report_id} deleted successfully.', 'success')
    return redirect(url_for('admin'))

@app.route('/alerts')
def alerts():
    all_alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template('alerts.html', alerts=all_alerts)

@app.route('/admin/create_alert', methods=['POST'])
def create_alert():
    title = request.form.get('title')
    message = request.form.get('message')
    alert_type = request.form.get('alert_type')
    
    if all([title, message, alert_type]):
        new_alert = Alert(
            title=title,
            message=message,
            alert_type=alert_type
        )
        db.session.add(new_alert)
        db.session.commit()
        flash('Alert broadcast successfully!', 'success')
    else:
        flash('Please fill in all alert fields.', 'danger')
    
    return redirect(url_for('alerts'))

@app.route('/visualization')
def visualization():
    return render_template('visualization.html')

@app.route('/api/statistics')
def get_statistics():
    total_reports = DisasterReport.query.count()
    verified_reports = DisasterReport.query.filter_by(status='verified').count()
    pending_reports = DisasterReport.query.filter_by(status='pending').count()
    resolved_reports = DisasterReport.query.filter_by(status='resolved').count()
    
    disaster_types = db.session.query(
        DisasterReport.disaster_type,
        db.func.count(DisasterReport.id)
    ).group_by(DisasterReport.disaster_type).all()
    
    severity_distribution = db.session.query(
        DisasterReport.severity,
        db.func.count(DisasterReport.id)
    ).group_by(DisasterReport.severity).all()
    
    recent_reports = db.session.query(
        db.func.date(DisasterReport.reported_at).label('date'),
        db.func.count(DisasterReport.id).label('count')
    ).group_by(db.func.date(DisasterReport.reported_at)).order_by('date').limit(30).all()
    
    return jsonify({
        'total_reports': total_reports,
        'verified_reports': verified_reports,
        'pending_reports': pending_reports,
        'resolved_reports': resolved_reports,
        'disaster_types': {dt: count for dt, count in disaster_types},
        'severity_distribution': {sev: count for sev, count in severity_distribution},
        'timeline': [{'date': str(date), 'count': count} for date, count in recent_reports]
    })

def seed_sample_data():
    if DisasterReport.query.count() == 0:
        sample_reports = [
            {
                'disaster_type': 'Earthquake',
                'location': 'Downtown City Center, Main Street',
                'severity': 'High',
                'description': 'Major earthquake measuring 6.5 on Richter scale. Multiple buildings damaged, infrastructure affected.',
                'reporter_name': 'John Smith',
                'reporter_contact': '+1-555-0101',
                'status': 'verified',
                'reported_at': datetime.utcnow() - timedelta(days=5)
            },
            {
                'disaster_type': 'Flood',
                'location': 'Riverside District, Valley Road',
                'severity': 'Critical',
                'description': 'Severe flooding due to heavy rainfall. Water level rising rapidly, evacuation needed.',
                'reporter_name': 'Sarah Johnson',
                'reporter_contact': '+1-555-0102',
                'status': 'verified',
                'reported_at': datetime.utcnow() - timedelta(days=3)
            },
            {
                'disaster_type': 'Fire',
                'location': 'Industrial Area, Factory Complex',
                'severity': 'High',
                'description': 'Large fire outbreak in industrial facility. Multiple fire units responding.',
                'reporter_name': 'Michael Brown',
                'reporter_contact': '+1-555-0103',
                'status': 'resolved',
                'reported_at': datetime.utcnow() - timedelta(days=10)
            },
            {
                'disaster_type': 'Cyclone',
                'location': 'Coastal Region, Beach Road',
                'severity': 'Critical',
                'description': 'Category 4 cyclone approaching. Strong winds and heavy rain expected.',
                'reporter_name': 'Emily Davis',
                'reporter_contact': '+1-555-0104',
                'status': 'verified',
                'reported_at': datetime.utcnow() - timedelta(days=1)
            },
            {
                'disaster_type': 'Landslide',
                'location': 'Hill Station, Mountain Road',
                'severity': 'Moderate',
                'description': 'Landslide blocking main highway. Traffic disrupted, road clearance in progress.',
                'reporter_name': 'Robert Wilson',
                'reporter_contact': '+1-555-0105',
                'status': 'pending',
                'reported_at': datetime.utcnow() - timedelta(hours=12)
            },
            {
                'disaster_type': 'Epidemic',
                'location': 'North District, Community Center',
                'severity': 'Moderate',
                'description': 'Outbreak of viral infection reported. Health officials monitoring situation.',
                'reporter_name': 'Lisa Anderson',
                'reporter_contact': '+1-555-0106',
                'status': 'verified',
                'reported_at': datetime.utcnow() - timedelta(days=7)
            },
            {
                'disaster_type': 'Drought',
                'location': 'Agricultural Zone, Farm Belt',
                'severity': 'High',
                'description': 'Severe water shortage affecting crops. Agricultural emergency declared.',
                'reporter_name': 'David Martinez',
                'reporter_contact': '+1-555-0107',
                'status': 'verified',
                'reported_at': datetime.utcnow() - timedelta(days=15)
            },
            {
                'disaster_type': 'Fire',
                'location': 'Forest Area, Pine Woods',
                'severity': 'Critical',
                'description': 'Wildfire spreading rapidly. Multiple areas evacuated, firefighters deployed.',
                'reporter_name': 'Jennifer Taylor',
                'reporter_contact': '+1-555-0108',
                'status': 'verified',
                'reported_at': datetime.utcnow() - timedelta(days=2)
            }
        ]
        
        for report_data in sample_reports:
            report = DisasterReport(**report_data)
            db.session.add(report)
        
        db.session.commit()
        print("Sample disaster reports added to database!")
    
    if Alert.query.count() == 0:
        sample_alerts = [
            {
                'title': 'Cyclone Warning - Coastal Areas',
                'message': 'A severe cyclone is expected to make landfall within 24 hours. Residents in coastal areas are advised to evacuate immediately and move to safe shelters.',
                'alert_type': 'Emergency',
                'created_at': datetime.utcnow() - timedelta(hours=6)
            },
            {
                'title': 'Flood Advisory - Riverside District',
                'message': 'Water levels are rising in the Riverside District due to continuous rainfall. Residents are advised to stay alert and avoid low-lying areas.',
                'alert_type': 'Warning',
                'created_at': datetime.utcnow() - timedelta(days=3)
            },
            {
                'title': 'Earthquake Safety Tips',
                'message': 'Following recent seismic activity, please review earthquake safety procedures. Drop, Cover, and Hold On during tremors.',
                'alert_type': 'Advisory',
                'created_at': datetime.utcnow() - timedelta(days=5)
            }
        ]
        
        for alert_data in sample_alerts:
            alert = Alert(**alert_data)
            db.session.add(alert)
        
        db.session.commit()
        print("Sample alerts added to database!")

@app.route('/admin/upload_csv', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin'))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        required_fields = ['disaster_type', 'location', 'severity', 'description', 'reporter_name', 'reporter_contact']
        
        added_count = 0
        for row in csv_reader:
            if all(field in row for field in required_fields):
                status = row.get('status', 'pending')
                if status not in ['pending', 'verified', 'resolved']:
                    status = 'pending'
                
                new_report = DisasterReport(
                    disaster_type=row['disaster_type'],
                    location=row['location'],
                    severity=row['severity'],
                    description=row['description'],
                    reporter_name=row['reporter_name'],
                    reporter_contact=row['reporter_contact'],
                    status=status
                )
                db.session.add(new_report)
                added_count += 1
        
        db.session.commit()
        flash(f'Successfully imported {added_count} disaster reports from CSV!', 'success')
        
    except Exception as e:
        flash(f'Error processing CSV file: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/download_template')
def download_template():
    template_data = [
        ['disaster_type', 'location', 'severity', 'description', 'reporter_name', 'reporter_contact', 'status'],
        ['Earthquake', 'Sample City', 'High', 'Sample earthquake description', 'John Doe', '+1-555-1234', 'pending'],
        ['Flood', 'Sample Town', 'Moderate', 'Sample flood description', 'Jane Smith', '+1-555-5678', 'verified']
    ]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(template_data)
    
    response = app.make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=disaster_reports_template.csv'
    
    return response

@app.before_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_sample_data()
    app.run(host='0.0.0.0', port=5000, debug=True)
