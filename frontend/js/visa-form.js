// Visa Form Handling
document.addEventListener('DOMContentLoaded', function() {
    // Form visibility toggle
    const showFormBtn = document.getElementById('show-i129-form');
    const i129Form = document.getElementById('i129-form-section');
    const documentRequirements = document.getElementById('h1b-document-requirements');
    
    if(showFormBtn) {
        showFormBtn.addEventListener('click', function() {
            i129Form.classList.remove('hidden');
            showFormBtn.classList.add('hidden');
            // Scroll to the form
            i129Form.scrollIntoView({ behavior: 'smooth' });
        });
    }
    
    // Handle conditional fields
    // Part 4: Passport explanation
    const passportRadios = document.querySelectorAll('input[name="validPassport"]');
    const passportExplanation = document.getElementById('passport-explanation');
    
    if(passportRadios.length) {
        passportRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'no') {
                    passportExplanation.classList.remove('hidden');
                    document.getElementById('passport-explanation-text').setAttribute('required', true);
                } else {
                    passportExplanation.classList.add('hidden');
                    document.getElementById('passport-explanation-text').removeAttribute('required');
                }
            });
        });
    }
    
    // Part 5: Third-party location
    const thirdPartyRadios = document.querySelectorAll('input[name="thirdParty1"]');
    const thirdPartyName = document.getElementById('third-party-name-1');
    
    if(thirdPartyRadios.length) {
        thirdPartyRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'yes') {
                    thirdPartyName.classList.remove('hidden');
                    document.getElementById('third-party-org-1').setAttribute('required', true);
                } else {
                    thirdPartyName.classList.add('hidden');
                    document.getElementById('third-party-org-1').removeAttribute('required');
                }
            });
        });
    }
    
    // Part 5: Full-time position
    const fullTimeRadios = document.querySelectorAll('input[name="fullTime"]');
    const partTimeHours = document.getElementById('part-time-hours');
    
    if(fullTimeRadios.length) {
        fullTimeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'no') {
                    partTimeHours.classList.remove('hidden');
                    document.getElementById('hours-per-week').setAttribute('required', true);
                } else {
                    partTimeHours.classList.add('hidden');
                    document.getElementById('hours-per-week').removeAttribute('required');
                }
            });
        });
    }
    
    // Form submission and validation
    const form = document.getElementById('i129-form');
    const formContainer = document.querySelector('.form-container');
    const formPageIndicator = document.getElementById('form-page-indicator');
    const docsPageIndicator = document.getElementById('documents-page-indicator');
    
    if(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Basic validation
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });
            
            if (isValid) {
                // Show loading indicator
                const submitBtn = form.querySelector('button[type="submit"]');
                const originalText = submitBtn.textContent;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                submitBtn.disabled = true;
                
                // Gather form data for potential API submission
                const formData = new FormData(form);
                const formDataObj = {};
                
                formData.forEach((value, key) => {
                    formDataObj[key] = value;
                });
                
                console.log('Form data:', formDataObj);
                
                // Simulate processing delay
                setTimeout(() => {
                    // Show success message and transition to page 2
                    document.getElementById('form-success-message').classList.remove('hidden');
                    
                    // Hide form container and show document requirements
                    setTimeout(() => {
                        // Update pagination indicators
                        formPageIndicator.classList.remove('active');
                        docsPageIndicator.classList.add('active');
                        
                        // Hide form and show documents
                        formContainer.classList.add('hidden');
                        documentRequirements.classList.remove('hidden');
                        documentRequirements.style.display = 'block';
                        
                        // Scroll to the top of documents section
                        i129Form.scrollIntoView({ behavior: 'smooth' });
                        
                        // Reset button
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                        
                        // Setup back button functionality
                        const backToFormBtn = document.getElementById('back-to-form');
                        if(backToFormBtn) {
                            backToFormBtn.addEventListener('click', function() {
                                // Hide documents and show form
                                documentRequirements.classList.add('hidden');
                                documentRequirements.style.display = 'none';
                                formContainer.classList.remove('hidden');
                                
                                // Update pagination indicators
                                docsPageIndicator.classList.remove('active');
                                formPageIndicator.classList.add('active');
                                
                                // Scroll to the top of form section
                                i129Form.scrollIntoView({ behavior: 'smooth' });
                            });
                        }
                    }, 1000);
                }, 1500);
                
                // In a real app, you would submit this data to your backend
                // submitFormToBackend(formDataObj);
            } else {
                // Show validation error
                const firstError = form.querySelector('.error');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Show error message
                alert('Please fill out all required fields.');
            }
        });
    }
    
    // Reset form button
    const resetBtn = document.getElementById('reset-form');
    if(resetBtn) {
        resetBtn.addEventListener('click', function() {
            form.reset();
            document.getElementById('form-success-message').classList.add('hidden');
        });
    }
    
    // Document upload handling
    const fileInputs = document.querySelectorAll('.document-upload input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0].name;
            const uploadStatus = this.closest('.document-upload').querySelector('.upload-status');
            uploadStatus.textContent = `Selected: ${fileName}`;
            uploadStatus.classList.add('file-selected');
        });
    });
});

// Function to simulate document upload
function uploadDocument(docType) {
    const fileInput = document.querySelector(`#${docType}-upload`);
    const uploadStatus = document.querySelector(`#${docType}-status`);
    
    if (fileInput.files.length === 0) {
        alert('Please select a file first.');
        return;
    }
    
    // Show loading
    uploadStatus.textContent = 'Uploading...';
    uploadStatus.className = 'upload-status uploading';
    
    // Simulate upload delay
    setTimeout(() => {
        uploadStatus.textContent = 'Uploaded successfully';
        uploadStatus.className = 'upload-status success';
        
        // Add to documents list
        const docName = fileInput.files[0].name;
        addToDocumentsList(docType, docName);
    }, 1500);
}

// Add document to the uploaded documents list
function addToDocumentsList(docType, fileName) {
    const docTypeMap = {
        'i129': 'Form I-129',
        'lca': 'Labor Condition Application',
        'education': 'Educational Credentials',
        'support': 'Employer Support Letter',
        'resume': 'Resume/CV'
    };
    
    const docList = document.getElementById('uploaded-documents-list');
    const listItem = document.createElement('li');
    listItem.className = 'document-item';
    listItem.innerHTML = `
        <div class="document-icon"><i class="far fa-file-pdf"></i></div>
        <div class="document-details">
            <h4>${docTypeMap[docType] || docType}</h4>
            <p>${fileName}</p>
            <span class="document-status approved">Verified</span>
        </div>
    `;
    
    docList.appendChild(listItem);
}
