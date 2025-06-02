from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from models import User, Petition, db
import re
from markupsafe import Markup

app = Flask(__name__)
app.secret_key = 'your-very-secure-secret-key'  # use a long, random key in production

# Define the nl2br filter
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        value = str(value)
        return Markup(value.replace('\n', '<br>\n'))
    return ''

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Venus%402002@localhost/immigraassist'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False  # Temporarily disable CSRF for testing

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)

# class User(db.Model):
#     __tablename__ = 'users'  # Must match your MySQL table name
#     id = db.Column(db.Integer, primary_key=True)
#     firstname = db.Column(db.String(80), nullable=False)
#     lastname = db.Column(db.String(80), nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     phone = db.Column(db.String(20), nullable=False)
#     password = db.Column(db.String(255), nullable=False)
#     role = db.Column(db.String(20), default='user')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('is_admin'):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def attorney_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not (session.get('is_admin') or session.get('is_attorney')):
            flash('Access denied. Attorney privileges required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_document_icon(doc_type):
    # Return appropriate FontAwesome icon class based on document type
    icon_map = {
        'Passport': 'fa-passport',
        'Birth Certificate': 'fa-file-alt',
        'Marriage Certificate': 'fa-file-contract',
        'Employment Letter': 'fa-file-signature',
        'Academic Transcript': 'fa-file-alt',
        'Tax Return': 'fa-file-invoice-dollar',
        'I-94 Record': 'fa-file-alt',
        'Previous Visa': 'fa-id-card'
    }
    
    # Return the mapped icon or a default icon if not found
    return icon_map.get(doc_type, 'fa-file')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Query user by email
        user = User.query.filter_by(email=email).first()

        print(user.firstname)

        if user and check_password_hash(user.password, password):
            session.clear()
            session['logged_in'] = True
            session['user_id'] = user.id
            session['is_admin'] = user.role == 'admin'
            session['is_attorney'] = user.role == 'attorney' or user.role == 'admin'  # Admin has attorney access
            session['attorney_name'] = f"{user.firstname} {user.lastname}" if user.role == 'attorney' or user.role == 'admin' else ''
            flash('Logged in successfully!', 'success')
            if user.role == 'admin' or user.role == 'attorney':
                return redirect(url_for('attorney'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form.get('firstName')
        lastname = request.form.get('lastName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
            phone=phone,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Get the current user's ID from session
    user_id = session.get('user_id')
    
    # Check if the user has any existing petitions
    existing_petition = None
    if user_id:
        existing_petition = Petition.query.filter_by(user_id=user_id).order_by(Petition.created_at.desc()).first()
    
    if request.method == 'POST':
        try:
            # Debug: Print form data
            print("\n" + "="*50)
            print("FORM SUBMISSION RECEIVED")
            print("="*50)
            print("Form submitted with data:")
            for key, value in request.form.items():
                print(f"{key}: {value}")
            print("="*50 + "\n")
            
            # Get the current user's ID from session
            user_id = session.get('user_id')
            
            # TEMPORARY SOLUTION FOR TESTING: Use admin user if no user is in session
            if not user_id:
                # Find admin user or create one if it doesn't exist
                admin_user = User.query.filter_by(email='admin@example.com').first()
                if not admin_user:
                    print("Creating admin user for testing")
                    admin_user = User(
                        firstname='Admin',
                        lastname='User',
                        email='admin@example.com',
                        phone='1234567890',
                        password=generate_password_hash('admin123'),
                        role='admin'
                    )
                    db.session.add(admin_user)
                    db.session.commit()
                
                user_id = admin_user.id
                print(f"Using admin user (id: {user_id}) for testing")
            else:
                # Verify the user exists in the database
                user = User.query.get(user_id)
                if not user:
                    # Find or create admin user as fallback
                    admin_user = User.query.filter_by(email='admin@example.com').first()
                    if not admin_user:
                        admin_user = User(
                            firstname='Admin',
                            lastname='User',
                            email='admin@example.com',
                            phone='1234567890',
                            password=generate_password_hash('admin123'),
                            role='admin'
                        )
                        db.session.add(admin_user)
                        db.session.commit()
                    
                    user_id = admin_user.id
                    print(f"User not found, using admin user (id: {user_id}) for testing")
                else:
                    print(f"Processing form for user_id: {user_id}, user: {user.email}")
            
            # Process birth date
            birth_date = None
            if request.form.get('birthDate'):
                try:
                    birth_date = datetime.strptime(request.form['birthDate'], '%Y-%m-%d')
                    print(f"Parsed birth date: {birth_date}")
                except ValueError as e:
                    print(f"Error parsing birth date: {e}")
                    flash('Invalid date format for birth date', 'error')
                    return redirect(url_for('dashboard'))
            
            # Create a new petition with form data
            petition = Petition(
                user_id=user_id,
                
                # Part 1: Petitioner Information
                petitioner_family_name=request.form['petitionerFamilyName'],
                petitioner_given_name=request.form['petitionerGivenName'],
                petitioner_middle_name=request.form.get('petitionerMiddleName', ''),
                company_name=request.form['companyName'],
                in_care_of=request.form.get('inCareOf', ''),
                street_address=request.form.get('streetAddress', ''),
                apt_ste_flr=request.form.get('aptSteFlr', ''),
                city=request.form.get('city', ''),
                state=request.form.get('state', ''),
                zip_code=request.form.get('zipCode', ''),
                province=request.form.get('province', ''),
                postal_code=request.form.get('postalCode', ''),
                country=request.form.get('country', ''),
                daytime_phone=request.form['daytimePhone'],
                mobile_phone=request.form.get('mobilePhone', ''),
                email=request.form['email'],
                fein=request.form['fein'],
                
                # Part 2: Basis for Classification
                basis_for_classification=request.form['basisForClassification'],
                
                # Part 3: Beneficiary Information
                beneficiary_family_name=request.form['beneficiaryFamilyName'],
                beneficiary_given_name=request.form['beneficiaryGivenName'],
                beneficiary_middle_name=request.form.get('beneficiaryMiddleName', ''),
                other_family_name=request.form.get('otherFamilyName', ''),
                other_given_name=request.form.get('otherGivenName', ''),
                other_middle_name=request.form.get('otherMiddleName', ''),
                birth_date=birth_date,
                gender=request.form.get('gender', ''),
                ssn=request.form.get('ssn', ''),
                alien_number=request.form.get('alienNumber', ''),
                country_of_birth=request.form['countryOfBirth'],
                country_of_citizenship=request.form['countryOfCitizenship'],
                passport_number=request.form['passportNumber'],
                passport_expiry_date=datetime.strptime(request.form['passportExpiryDate'], '%Y-%m-%d'),
                education_qualification=request.form['educationQualification'],
                
                # Part 4: Processing Information
                foreign_street=request.form.get('foreignStreet', ''),
                foreign_apt=request.form.get('foreignApt', ''),
                foreign_city=request.form.get('foreignCity', ''),
                foreign_state=request.form.get('foreignState', ''),
                foreign_postal=request.form.get('foreignPostal', ''),
                foreign_country=request.form.get('foreignCountry', ''),
                valid_passport=request.form.get('validPassport', ''),
                passport_explanation=request.form.get('passportExplanation', ''),
                
                # Part 5: Basic Information About Proposed Employment
                job_title=request.form['jobTitle'],
                lca_number=request.form['lcaNumber'],
                work_street_1=request.form.get('workStreet1', ''),
                work_apt_1=request.form.get('workApt1', ''),
                work_city_1=request.form.get('workCity1', ''),
                work_state_1=request.form.get('workState1', ''),
                work_zip_1=request.form.get('workZip1', ''),
                third_party_1=request.form.get('thirdParty1', 'no'),
                third_party_org_1=request.form.get('thirdPartyOrg1', ''),
                itinerary=request.form.get('itinerary', 'no'),
                work_offsite=request.form.get('workOffsite', 'no'),
                full_time=request.form.get('fullTime', 'yes'),
                hours_per_week=int(request.form.get('hoursPerWeek', 0)) if request.form.get('hoursPerWeek') else None,
                wage_amount=float(request.form.get('wageAmount', 0)) if request.form.get('wageAmount') else 0,
                wage_period=request.form.get('wagePeriod', '')
            )
            
            print("Petition object created successfully")
            
            # Add to database and commit
            db.session.add(petition)
            print("Petition added to session")
            db.session.commit()
            print("Database commit successful")
            
            # Show success message
            flash('Petition submitted successfully!', 'success')
            
            # Return a response that will trigger the document requirements page
            return render_template('dashboard.html', 
                                  show_documents=True, 
                                  petition_submitted=True)

        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting petition: {str(e)}', 'error')
            print(f"Exception details: {str(e)}")
            # Print the full traceback for debugging
            import traceback
            traceback.print_exc()

    return render_template('dashboard.html', existing_petition=existing_petition)
    
@app.route('/services')
@login_required
def services():
    return render_template('services.html')

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'message': 'Cannot delete yourself'})
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/attorney')
@login_required
@attorney_required
def attorney():
    # Get petitions for this attorney to review
    petitions = Petition.query.all()
    
    # Add simulated data for demonstration
    for petition in petitions:
        # Randomly assign status
        import random
        statuses = ['Pending', 'Under Review', 'Approved', 'Rejected']
        petition.status = random.choice(statuses)
        
        # Assign completion percentage
        if petition.status == 'Approved':
            petition.completion_percentage = 100
        elif petition.status == 'Rejected':
            petition.completion_percentage = 100
        elif petition.status == 'Under Review':
            petition.completion_percentage = random.randint(50, 90)
        else:
            petition.completion_percentage = random.randint(10, 40)
    
    # Simulated recent activities
    recent_activities = [
        {
            'icon': 'fas fa-file-upload',
            'description': 'New document uploaded for John Smith\'s H-1B petition',
            'timestamp': 'Today, 2:30 PM'
        },
        {
            'icon': 'fas fa-user-edit',
            'description': 'Updated client information for Maria Garcia',
            'timestamp': 'Today, 11:15 AM'
        },
        {
            'icon': 'fas fa-check-circle',
            'description': 'David Lee\'s H-1B petition approved',
            'timestamp': 'Yesterday, 4:45 PM'
        }
    ]
    
    return render_template('attorney.html', 
                          petitions=petitions,
                          recent_activities=recent_activities)

@app.route('/attorney/cases')
@login_required
@attorney_required
def attorney_cases():
    # Simulate active cases
    active_cases = []
    for i in range(1, 8):
        case_types = ['H-1B', 'Green Card', 'PERM', 'L-1', 'O-1', 'I-130', 'I-485']
        statuses = ['Initial Review', 'Request for Evidence', 'Preparing Documents', 'Ready for Filing', 'Filed']
        
        active_cases.append({
            'id': i,
            'client_name': f'Client {i}',
            'visa_type': case_types[i-1],
            'status': statuses[i % len(statuses)],
            'priority_date': f'2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
            'last_updated': f'{i} days ago'
        })
    
    # Simulate archived cases
    archived_cases = []
    for i in range(8, 12):
        case_types = ['H-1B', 'Green Card', 'PERM', 'L-1']
        outcomes = ['Approved', 'Denied', 'Withdrawn', 'Approved']
        
        archived_cases.append({
            'id': i,
            'client_name': f'Client {i}',
            'visa_type': case_types[i % len(case_types)],
            'outcome': outcomes[i % len(outcomes)],
            'close_date': f'2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
            'notes': 'Case completed successfully' if 'Approved' in outcomes[i % len(outcomes)] else 'Case unsuccessful'
        })
    
    return render_template('attorney_cases.html', 
                          active_cases=active_cases,
                          archived_cases=archived_cases)

@app.route('/attorney/clients')
@login_required
@attorney_required
def attorney_clients():
    # Get page parameter from query string, default to 1
    page = request.args.get('page', 1, type=int)
    
    # Simulate client list
    all_clients = []
    for i in range(1, 20):  # Create more clients to demonstrate pagination
        status = 'Active' if i % 3 != 0 else 'Inactive'
        all_clients.append({
            'id': i,
            'firstname': f'First{i}',
            'lastname': f'Last{i}',
            'email': f'client{i}@example.com',
            'phone': f'555-000-{1000+i}',
            'status': status,
            'cases': [{'id': j, 'type': 'Case Type'} for j in range(1, i % 3 + 2)],
            'join_date': f'2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
            'notes': f'Client notes for client {i}\nMultiple lines of notes\nShowing nl2br filter'
        })
    
    # Pagination logic
    items_per_page = 10
    total_clients = len(all_clients)
    
    # Calculate start and end indices for the current page
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_clients)
    
    # Get clients for the current page
    clients = all_clients[start_idx:end_idx]
    
    # Determine if there are more pages
    has_next = end_idx < total_clients
    
    return render_template('attorney_clients.html', 
                           clients=clients, 
                           page=page,
                           total_clients=total_clients,
                           has_next=has_next)

@app.route('/attorney/forms')
@login_required
@attorney_required
def attorney_forms():
    # Simulate immigration forms
    form_categories = {
        'Employment-Based': [
            {'id': 'I-129', 'name': 'Petition for Nonimmigrant Worker', 'description': 'For H-1B, L, O, and other employment-based temporary visas', 'last_updated': '2023-03-15'},
            {'id': 'I-140', 'name': 'Immigrant Petition for Alien Worker', 'description': 'For employment-based green cards', 'last_updated': '2023-01-20'},
            {'id': 'ETA-9089', 'name': 'PERM Labor Certification', 'description': 'Required for many employment-based green cards', 'last_updated': '2023-05-01'}
        ],
        'Family-Based': [
            {'id': 'I-130', 'name': 'Petition for Alien Relative', 'description': 'For family-based immigration', 'last_updated': '2023-02-28'},
            {'id': 'I-485', 'name': 'Application to Register Permanent Residence', 'description': 'Adjustment of status to permanent resident', 'last_updated': '2023-04-10'},
            {'id': 'I-751', 'name': 'Petition to Remove Conditions on Residence', 'description': 'For conditional permanent residents through marriage', 'last_updated': '2023-03-15'}
        ],
        'Citizenship': [
            {'id': 'N-400', 'name': 'Application for Naturalization', 'description': 'For U.S. citizenship', 'last_updated': '2023-01-05'},
            {'id': 'N-600', 'name': 'Application for Certificate of Citizenship', 'description': 'For claiming citizenship through parents', 'last_updated': '2022-11-30'}
        ],
        'Humanitarian': [
            {'id': 'I-589', 'name': 'Application for Asylum and Withholding of Removal', 'description': 'For asylum seekers', 'last_updated': '2023-04-22'},
            {'id': 'I-918', 'name': 'Petition for U Nonimmigrant Status', 'description': 'For victims of crimes', 'last_updated': '2022-12-15'}
        ]
    }
    
    return render_template('attorney_forms.html', form_categories=form_categories)

@app.route('/attorney/documents')
@login_required
@attorney_required
def attorney_documents():
    # Simulate clients for document filtering
    clients = []
    for i in range(1, 10):
        clients.append({
            'id': i,
            'name': f'Client {i}'
        })
    
    # Simulate documents
    documents = []
    doc_types = ['Passport', 'Birth Certificate', 'Marriage Certificate', 'Employment Letter', 
                'Academic Transcript', 'Tax Return', 'I-94 Record', 'Previous Visa']
    
    for i in range(1, 20):
        doc_type = doc_types[i % len(doc_types)]
        client_id = (i % 9) + 1
        
        documents.append({
            'id': i,
            'name': f'{doc_type} - Client {client_id}',
            'type': doc_type,
            'client_id': client_id,
            'client_name': f'Client {client_id}',
            'upload_date': f'2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
            'size': (i % 10) + 1,
            'size_formatted': f'{(i % 10) + 1} MB',
            'icon': get_document_icon(doc_type),
            'case_id': i if i % 4 == 0 else None,
            'shared': (i % 3 == 0)
        })
    
    return render_template('attorney_documents.html', documents=documents, clients=clients)


@app.route('/attorney/upload-document', methods=['POST'])
@login_required
@attorney_required
def upload_attorney_document():
    # In a real application, handle file upload with request.files
    # For this simulation, we'll just return a success response
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '')
        document_type = request.form.get('type', 'other')
        client_id = request.form.get('client_id', '')
        case_id = request.form.get('case_id', '')
        
        # Simulate file upload processing
        # In a real app, you would save the file and store metadata in the database
        
        # Return success response
        return jsonify({
            'success': True,
            'message': f'Document "{name}" uploaded successfully',
            'document': {
                'id': 999,  # Simulated new document ID
                'name': name,
                'type': document_type,
                'client_id': int(client_id) if client_id.isdigit() else None,
                'client_name': f'Client {client_id}' if client_id.isdigit() else 'No Client',
                'case_id': int(case_id) if case_id.isdigit() else None,
                'upload_date': datetime.now().strftime('%Y-%m-%d'),
                'size_formatted': '2.5 MB',  # Simulated file size
                'icon': get_document_icon(document_type),
                'shared': False
            }
        })


@app.route('/petition/<int:petition_id>', endpoint='attorney_petition_details')
@login_required
@attorney_required
def petition_details(petition_id):
    # Simulate petition data
    petition = {
        'id': petition_id,
        'type': 'H-1B Visa',
        'status': 'Under Review',
        'priority_date': '2023-05-15',
        'completion_percentage': 65,
        'petitioner': {
            'name': 'ABC Tech Corporation',
            'contact': 'John Smith',
            'email': 'jsmith@abctech.com',
            'phone': '555-123-4567',
            'address': '123 Corporate Way, San Francisco, CA 94107'
        },
        'beneficiary': {
            'name': 'Jane Doe',
            'email': 'jane.doe@example.com',
            'phone': '555-987-6543',
            'nationality': 'India',
            'current_status': 'F-1 Student',
            'address': '456 University Ave, Palo Alto, CA 94301'
        },
        'position': {
            'title': 'Senior Software Engineer',
            'duties': 'Design and develop software applications, lead technical projects, mentor junior developers.',
            'requirements': 'Master\'s degree in Computer Science or related field, 5+ years experience in software development.',
            'salary': '$150,000 per year',
            'location': 'San Francisco, CA'
        },
        'timeline': [
            {'date': '2023-05-15', 'event': 'Petition filed', 'status': 'complete'},
            {'date': '2023-05-20', 'event': 'Initial review', 'status': 'complete'},
            {'date': '2023-06-10', 'event': 'RFE received', 'status': 'complete'},
            {'date': '2023-06-25', 'event': 'RFE response submitted', 'status': 'complete'},
            {'date': '2023-07-15', 'event': 'Final review', 'status': 'in-progress'},
            {'date': 'Pending', 'event': 'Decision', 'status': 'pending'}
        ],
        'documents': [
            {'name': 'Form I-129', 'status': 'submitted', 'date': '2023-05-15'},
            {'name': 'Labor Condition Application', 'status': 'submitted', 'date': '2023-05-15'},
            {'name': 'Employer Support Letter', 'status': 'submitted', 'date': '2023-05-15'},
            {'name': 'Beneficiary Resume', 'status': 'submitted', 'date': '2023-05-15'},
            {'name': 'Educational Credentials', 'status': 'submitted', 'date': '2023-05-15'},
            {'name': 'RFE Response', 'status': 'submitted', 'date': '2023-06-25'}
        ],
        'notes': 'Client has requested expedited processing. Beneficiary\'s current status expires in 3 months.\nRFE requested additional evidence of specialized knowledge.'
    }
    
    return render_template('petition_details.html', petition=petition)

@app.route('/attorney/calendar')
@login_required
@attorney_required
def attorney_calendar():
    import datetime
    
    # Current date for generating events
    now = datetime.datetime.now()
    
    # Simulate clients
    clients = []
    for i in range(1, 10):
        clients.append({
            'id': i,
            'firstname': f'First{i}',
            'lastname': f'Last{i}'
        })
    
    # Simulate calendar events
    calendar_events = []
    event_types = ['appointment', 'deadline', 'court', 'consultation', 'reminder']
    event_colors = {
        'appointment': '#4299e1',
        'deadline': '#f56565',
        'court': '#805ad5',
        'consultation': '#38a169',
        'reminder': '#ecc94b',
        'other': '#a0aec0'
    }
    
    # Generate events for the next 30 days
    for i in range(1, 20):
        event_type = event_types[i % len(event_types)]
        event_date = now + datetime.timedelta(days=i % 30)
        client_id = (i % 9) + 1 if i % 3 == 0 else None
        
        event = {
            'id': i,
            'title': f'{event_type.capitalize()} {i}',
            'start': event_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'end': (event_date + datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'),
            'color': event_colors[event_type],
            'eventType': event_type,
            'description': f'Description for {event_type} {i}'
        }
        
        if client_id:
            event['clientName'] = f'Client {client_id}'
            event['clientId'] = client_id
            
            # Sometimes add a case ID
            if i % 5 == 0:
                event['caseId'] = i + 100
        
        if i % 4 == 0:
            event['location'] = 'Office' if i % 2 == 0 else 'Video Conference'
            
        calendar_events.append(event)
    
    # Upcoming events (next 5 events)
    upcoming_events = []
    for i in range(1, 6):
        event_date = now + datetime.timedelta(days=i, hours=i)
        event_type = event_types[i % len(event_types)]
        client_id = (i % 9) + 1 if i % 2 == 0 else None
        
        event = {
            'id': i + 100,
            'title': f'{event_type.capitalize()} with Client {client_id}' if client_id else f'{event_type.capitalize()} {i}',
            'start_time': event_date,
            'end_time': event_date + datetime.timedelta(hours=1),
            'color': event_colors[event_type]
        }
        
        if client_id:
            event['client_name'] = f'Client {client_id}'
            
        upcoming_events.append(event)
    
    return render_template('attorney_calendar.html', 
                          calendar_events=calendar_events,
                          upcoming_events=upcoming_events,
                          clients=clients)

@app.route('/attorney/settings')
@login_required
@attorney_required
def attorney_settings():
    # Get current user
    user_id = session.get('user_id')
    attorney = User.query.get(user_id)
    
    # Simulate attorney preferences
    if not hasattr(attorney, 'preferences'):
        attorney.preferences = {
            'theme': 'light',
            'dashboard_layout': 'detailed',
            'default_calendar_view': 'month'
        }
    
    # Simulate notification settings
    if not hasattr(attorney, 'notifications'):
        attorney.notifications = {
            'email_new_cases': True,
            'email_case_updates': True,
            'email_deadlines': True,
            'email_appointments': True,
            'system_messages': True,
            'system_client_messages': True
        }
    
    # Simulate two-factor authentication status
    if not hasattr(attorney, 'two_factor_enabled'):
        attorney.two_factor_enabled = False
    
    # For demonstration purposes
    attorney.bar_number = 'ABC12345'
    attorney.jurisdiction = 'New York State'
    attorney.practice_areas = ['family', 'employment']
    attorney.bio = 'Experienced immigration attorney with 10+ years of practice.'
    
    return render_template('attorney_settings.html', attorney=attorney)

# API routes for attorney functions

@app.route('/attorney/get-client-cases/<int:client_id>')
@login_required
@attorney_required
def get_client_cases(client_id):
    # Simulate cases for the client
    cases = []
    case_types = ['H-1B', 'Green Card', 'PERM', 'L-1', 'O-1']
    
    for i in range(1, 4):
        cases.append({
            'id': client_id * 10 + i,
            'visa_type': case_types[i % len(case_types)],
            'status': 'Active'
        })
    
    return jsonify({'success': True, 'cases': cases})

@app.route('/attorney/add-client', methods=['POST'])
@login_required
@attorney_required
def add_client():
    # In a real application, validate and save to database
    return jsonify({'success': True, 'message': 'Client added successfully'})

@app.route('/attorney/edit-client/<int:client_id>', methods=['POST'])
@login_required
@attorney_required
def edit_client(client_id):
    # In a real application, validate and update database
    return jsonify({'success': True, 'message': 'Client updated successfully'})

@app.route('/attorney/toggle-client-status/<int:client_id>', methods=['POST'])
@login_required
@attorney_required
def toggle_client_status(client_id):
    # In a real application, update status in database
    return jsonify({'success': True, 'message': 'Client status updated'})

@app.route('/attorney/upload-document', methods=['POST'])
@login_required
@attorney_required
def upload_document():
    # In a real application, validate and save file to storage
    return jsonify({'success': True, 'message': 'Document uploaded successfully'})

@app.route('/attorney/share-document/<int:document_id>', methods=['POST'])
@login_required
@attorney_required
def share_document(document_id):
    # In a real application, update sharing settings in database
    return jsonify({'success': True, 'message': 'Document shared successfully'})

@app.route('/attorney/delete-document/<int:document_id>', methods=['POST'])
@login_required
@attorney_required
def delete_document(document_id):
    # In a real application, delete from storage and database
    return jsonify({'success': True, 'message': 'Document deleted successfully'})

@app.route('/attorney/add-calendar-event', methods=['POST'])
@login_required
@attorney_required
def add_calendar_event():
    # In a real application, validate and save to database
    return jsonify({'success': True, 'message': 'Event added successfully'})

@app.route('/attorney/edit-event/<int:event_id>', methods=['POST'])
@login_required
@attorney_required
def edit_calendar_event(event_id):
    # In a real application, validate and update database
    return jsonify({'success': True, 'message': 'Event updated successfully'})

@app.route('/attorney/delete-event/<int:event_id>', methods=['POST'])
@login_required
@attorney_required
def delete_calendar_event(event_id):
    # In a real application, delete from database
    return jsonify({'success': True, 'message': 'Event deleted successfully'})

@app.route('/attorney/update-attorney-profile', methods=['POST'])
@login_required
@attorney_required
def update_attorney_profile():
    # In a real application, validate and update database
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

@app.route('/attorney/update-attorney-password', methods=['POST'])
@login_required
@attorney_required
def update_attorney_password():
    # In a real application, validate and update database
    return jsonify({'success': True, 'message': 'Password updated successfully'})

@app.route('/attorney/update-attorney-notifications', methods=['POST'])
@login_required
@attorney_required
def update_attorney_notifications():
    # In a real application, validate and update database
    return jsonify({'success': True, 'message': 'Notification preferences updated'})

@app.route('/attorney/update-attorney-preferences', methods=['POST'])
@login_required
@attorney_required
def update_attorney_preferences():
    # In a real application, validate and update database
    return jsonify({'success': True, 'message': 'Preferences updated successfully'})

@app.route('/attorney/enable-two-factor', methods=['POST'])
@login_required
@attorney_required
def enable_two_factor():
    # In a real application, validate code and enable 2FA
    return jsonify({'success': True, 'message': 'Two-factor authentication enabled'})

@app.route('/attorney/disable-two-factor', methods=['POST'])
@login_required
@attorney_required
def disable_two_factor():
    # In a real application, validate password and disable 2FA
    return jsonify({'success': True, 'message': 'Two-factor authentication disabled'})


@app.route('/attorney/petition/<int:petition_id>')
@login_required
@attorney_required
def petition_details(petition_id):
    petition = Petition.query.get_or_404(petition_id)
    
    # Simulated data for petition progress
    import random
    progress_steps = [
        {'name': 'Initial Review', 'status': 'completed', 'date': '2025-05-15'},
        {'name': 'Document Collection', 'status': 'completed', 'date': '2025-05-20'},
        {'name': 'Form Preparation', 'status': 'in-progress', 'date': '2025-05-25'},
        {'name': 'Attorney Review', 'status': 'pending', 'date': ''},
        {'name': 'USCIS Submission', 'status': 'pending', 'date': ''},
        {'name': 'USCIS Processing', 'status': 'pending', 'date': ''},
        {'name': 'Decision', 'status': 'pending', 'date': ''}
    ]
    
    # Simulated document status
    documents = [
        {'name': 'Passport', 'status': 'submitted', 'date': '2025-05-16'},
        {'name': 'Resume/CV', 'status': 'submitted', 'date': '2025-05-17'},
        {'name': 'Educational Credentials', 'status': 'submitted', 'date': '2025-05-18'},
        {'name': 'Employment Verification Letter', 'status': 'missing', 'date': ''},
        {'name': 'Previous Visa Documentation', 'status': 'submitted', 'date': '2025-05-19'},
        {'name': 'I-129 Form', 'status': 'in-progress', 'date': '2025-05-25'}
    ]
    
    return render_template('petition_details.html', 
                          petition=petition,
                          progress_steps=progress_steps,
                          documents=documents)

@app.route('/attorney/submit-attorney-form', methods=['POST'])
@login_required
@attorney_required
def submit_attorney_form():
    # Process the attorney-filled form submission
    if request.method == 'POST':
        # Handle form data processing here
        petition_id = request.form.get('petition_id')
        form_type = request.form.get('form_type')
        
        # Save form data logic would go here
        
        flash('Form submitted successfully!', 'success')
        return redirect(url_for('petition_details', petition_id=petition_id))
    
    return redirect(url_for('attorney'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            admin = User(
                firstname='Admin',
                lastname='User',
                email='admin@example.com',
                phone='1234567890',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            
        # Create attorney user if it doesn't exist
        attorney_user = User.query.filter_by(email='attorney@example.com').first()
        if not attorney_user:
            attorney = User(
                firstname='Jane',
                lastname='Attorney',
                email='attorney@example.com',
                phone='9876543210',
                password=generate_password_hash('attorney123'),
                role='attorney'
            )
            db.session.add(attorney)
            db.session.commit()
            
    app.run(debug=True)
