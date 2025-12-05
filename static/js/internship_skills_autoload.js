// Auto-load skills based on selected course for internship creation/edit (coordinator)
document.addEventListener('DOMContentLoaded', function() {
    const courseSelect = document.getElementById('id_course');
    const skillsCheckboxes = document.querySelectorAll('input[name="skills"]');
    if (!courseSelect || !skillsCheckboxes.length) return;

    const COURSE_SKILLS_MAP = {
        'BSIT': ['Programming', 'Web Development', 'Database Management', 'Networking'],
        'BSCS': ['Algorithms', 'Software Engineering', 'AI', 'Data Structures'],
        'BSPSY': ['Counseling', 'Research', 'Psychological Assessment'],
        'BSCRIM': ['Forensics', 'Law Enforcement', 'Investigation'],
        'BSED_MATH': ['Mathematics', 'Teaching', 'Statistics'],
        'BSED_ENG': ['English', 'Teaching', 'Literature'],
        'BSHM': ['Hospitality', 'Event Management', 'Culinary'],
        'BSBM_MKT': ['Marketing', 'Sales', 'Advertising'],
        'BSBM_HR': ['Human Resources', 'Recruitment', 'Training'],
    };

    function updateSkills() {
        const selected = courseSelect.value;
        const skills = COURSE_SKILLS_MAP[selected] || [];
        skillsCheckboxes.forEach(cb => {
            const label = cb.parentElement.textContent.trim();
            cb.checked = skills.includes(label);
        });
    }

    courseSelect.addEventListener('change', updateSkills);
    updateSkills();
});
