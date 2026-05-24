// Modern skill selection: chip UI, custom skills, and hidden field for Django form
// Uses COURSE_SKILLS_MAP and INITIAL_SELECTED_SKILLS from Django context

document.addEventListener('DOMContentLoaded', function() {
    // Use the course dropdown directly for multi-select
    const courseDropdown = document.getElementById('id_recommended_courses') || document.getElementById('id_course');
    const selectedSkillsDiv = document.getElementById('selected-skills');
    const searchInput = document.getElementById('skill-search-input') || document.getElementById('custom-skill-input');
    const suggestionsDiv = document.getElementById('skill-suggestions');
    const addCustomSkillBtn = document.getElementById('add-custom-skill');
    const skillsJsonInput = document.getElementById('id_skills_json');

    if (!searchInput || !selectedSkillsDiv || !skillsJsonInput) {
        return;
    }

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

    function renderSuggestions(query) {
        if (!suggestionsDiv) {
            return;
        }
        const trimmed = (query || '').trim().toLowerCase();
        suggestionsDiv.innerHTML = '';
        if (!trimmed && document.activeElement !== searchInput) {
            return;
        }
        const courseIds = getSelectedCourseIds();
        const skills = getUnionSkills(courseIds);
        const filtered = skills.filter(skill => {
            if (selectedSkills.some(s => s.id === skill.id && !s.custom)) {
                return false;
            }
            if (!trimmed) {
                return true;
            }
            return skill.name.toLowerCase().includes(trimmed);
        }).slice(0, 8);

        if (!filtered.length) {
            const empty = document.createElement('div');
            empty.className = 'skill-suggestion-empty';
            empty.textContent = 'No suggestions. Press Enter to add as custom.';
            suggestionsDiv.appendChild(empty);
            return;
        }

        filtered.forEach(skill => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'skill-suggestion-item';
            item.textContent = skill.name;
            const selectSkill = function(e) {
                if (e) {
                    e.preventDefault();
                }
                addSkill({id: skill.id, name: skill.name, custom: false});
                searchInput.value = '';
                renderSuggestions('');
            };
            item.addEventListener('pointerdown', selectSkill);
            item.addEventListener('touchstart', selectSkill);
            item.addEventListener('click', selectSkill);
            suggestionsDiv.appendChild(item);
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

    function addSkill(skill) {
        const exists = selectedSkills.some(s => {
            if (skill.custom) {
                return s.custom && s.name.toLowerCase() === skill.name.toLowerCase();
            }
            return s.id === skill.id && !s.custom;
        });
        if (!exists) {
            selectedSkills.push(skill);
            renderSelectedSkills();
        }
    }

    function removeSkill(skill) {
        selectedSkills = selectedSkills.filter(s => {
            if (skill.custom) {
                return !(s.custom && s.name === skill.name);
            } else {
                return !(s.id === skill.id && !s.custom);
            }
        });
        renderSelectedSkills();
    }

    function addSkillFromInput() {
        const val = searchInput.value.trim();
        if (!val) {
            return;
        }
        const courseIds = getSelectedCourseIds();
        const skills = getUnionSkills(courseIds);
        const matched = skills.find(skill => skill.name.toLowerCase() === val.toLowerCase());
        if (matched) {
            addSkill({id: matched.id, name: matched.name, custom: false});
        } else {
            addSkill({id: null, name: val, custom: true});
        }
        searchInput.value = '';
        renderSuggestions('');
    }

    if (addCustomSkillBtn) {
        addCustomSkillBtn.addEventListener('click', addSkillFromInput);
    }

    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSkillFromInput();
        }
    });

    searchInput.addEventListener('input', function() {
        renderSuggestions(searchInput.value);
    });

    searchInput.addEventListener('focus', function() {
        renderSuggestions(searchInput.value);
    });

    searchInput.addEventListener('blur', function() {
        if (!suggestionsDiv) {
            return;
        }
        setTimeout(function() {
            suggestionsDiv.innerHTML = '';
        }, 150);
    });

    if (suggestionsDiv) {
        suggestionsDiv.addEventListener('mousedown', function(e) {
            e.preventDefault();
        });
        suggestionsDiv.addEventListener('touchstart', function(e) {
            e.preventDefault();
        });
    }

    if (courseDropdown) {
        courseDropdown.addEventListener('change', function() {
            // Remove all non-custom selected skills when course changes
            selectedSkills = selectedSkills.filter(s => s.custom);
            renderSelectedSkills();
            renderSuggestions(searchInput.value);
        });
        // For multi-select, also listen for input events
        if (courseDropdown.multiple) {
            courseDropdown.addEventListener('input', function() {
                renderSuggestions(searchInput.value);
            });
        }
    }

    // Initialize with any pre-selected skills
    if (typeof INITIAL_SELECTED_SKILLS !== 'undefined') {
        INITIAL_SELECTED_SKILLS.forEach(skill => {
            selectedSkills.push({id: skill.id, name: skill.name, custom: false});
        });
    }
    renderSelectedSkills();
    renderSuggestions('');
});
