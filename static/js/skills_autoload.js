// Modern skill selection: chip UI, custom skills, and hidden field for Django form
// Uses COURSE_SKILLS_MAP and INITIAL_SELECTED_SKILLS from Django context

document.addEventListener('DOMContentLoaded', function() {
    // Use the course dropdown directly for multi-select
    const courseDropdown = document.getElementById('id_recommended_courses') || document.getElementById('id_course');
    const skillChipsDiv = document.getElementById('skill-chips');
    const selectedSkillsDiv = document.getElementById('selected-skills');
    const customSkillInput = document.getElementById('custom-skill-input');
    const addCustomSkillBtn = document.getElementById('add-custom-skill');
    const skillsJsonInput = document.getElementById('id_skills_json');

    let selectedSkills = [];

    function getSelectedCourseIds() {
        // For multi-select dropdown
        if (courseDropdown && courseDropdown.multiple) {
            return Array.from(courseDropdown.selectedOptions).map(opt => opt.value).filter(Boolean);
        }
        // For hidden field fallback (single select)
        if (courseDropdown && courseDropdown.value) {
            return courseDropdown.value.split(',').filter(Boolean);
        }
        return [];
    }

    function getUnionSkills(courseIds) {
        const skillMap = {};
        courseIds.forEach(cid => {
            (COURSE_SKILLS_MAP[cid] || []).forEach(skill => {
                skillMap[skill.id] = skill;
            });
        });
        return Object.values(skillMap);
    }

    function renderSkillChips() {
        skillChipsDiv.innerHTML = '';
        const courseIds = getSelectedCourseIds();
        const skills = getUnionSkills(courseIds);
        skills.forEach(skill => {
            const chip = document.createElement('span');
            chip.className = 'badge rounded-pill bg-light text-dark border me-1 mb-1 skill-chip';
            chip.textContent = skill.name;
            chip.dataset.id = skill.id;
            chip.style.cursor = 'pointer';
            if (selectedSkills.some(s => s.id === skill.id && !s.custom)) {
                chip.classList.add('bg-primary', 'text-white');
            }
            chip.addEventListener('click', function() {
                toggleSkill({id: skill.id, name: skill.name, custom: false});
            });
            skillChipsDiv.appendChild(chip);
        });
    }

    function renderSelectedSkills() {
        selectedSkillsDiv.innerHTML = '';
        selectedSkills.forEach(skill => {
            const chip = document.createElement('span');
            chip.className = 'badge rounded-pill bg-success text-white me-1 mb-1';
            chip.textContent = skill.name + ' ×';
            chip.style.cursor = 'pointer';
            chip.addEventListener('click', function() {
                removeSkill(skill);
            });
            selectedSkillsDiv.appendChild(chip);
        });
        // Update hidden field
        skillsJsonInput.value = JSON.stringify(selectedSkills);
    }

    function toggleSkill(skill) {
        const idx = selectedSkills.findIndex(s => s.id === skill.id && !s.custom);
        if (idx === -1) {
            selectedSkills.push(skill);
        } else {
            selectedSkills.splice(idx, 1);
        }
        renderSkillChips();
        renderSelectedSkills();
    }

    function removeSkill(skill) {
        selectedSkills = selectedSkills.filter(s => {
            if (skill.custom) {
                return !(s.custom && s.name === skill.name);
            } else {
                return !(s.id === skill.id && !s.custom);
            }
        });
        renderSkillChips();
        renderSelectedSkills();
    }

    addCustomSkillBtn.addEventListener('click', function() {
        const val = customSkillInput.value.trim();
        if (val && !selectedSkills.some(s => s.custom && s.name.toLowerCase() === val.toLowerCase())) {
            selectedSkills.push({id: null, name: val, custom: true});
            customSkillInput.value = '';
            renderSelectedSkills();
        }
    });
    customSkillInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addCustomSkillBtn.click();
        }
    });

    if (courseDropdown) {
        courseDropdown.addEventListener('change', function() {
            // Remove all non-custom selected skills when course changes
            selectedSkills = selectedSkills.filter(s => s.custom);
            renderSkillChips();
            renderSelectedSkills();
        });
        // For multi-select, also listen for input events
        if (courseDropdown.multiple) {
            courseDropdown.addEventListener('input', function() {
                renderSkillChips();
                renderSelectedSkills();
            });
        }
    }

    // Initialize with any pre-selected skills
    if (typeof INITIAL_SELECTED_SKILLS !== 'undefined') {
        INITIAL_SELECTED_SKILLS.forEach(skill => {
            selectedSkills.push({id: skill.id, name: skill.name, custom: false});
        });
    }
    renderSkillChips();
    renderSelectedSkills();
});
