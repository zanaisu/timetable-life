# Current Notes

## Template Syntax Issues (3/10/2025)

### JavaScript Interaction in Templates

**Key Files with Issues:**
- app/templates/main/progress.html
- app/templates/main/index.html
- app/templates/main/curriculum.html

**Common Error Pattern:**
When using Jinja2 template variables directly within JavaScript contexts (especially event handlers), proper quoting and type handling is crucial. 

**Issues Found:**
1. Directly embedding template variables in onclick handlers creates syntax errors
2. Using template variables in JavaScript expressions without proper type conversion
3. Complex inline template conditionals affecting JavaScript syntax
4. Multiple class attributes on HTML elements

**Solutions Applied:**
1. For simple variable parameters, properly quote values in handlers:
   ```html
   <!-- INCORRECT -->
   onclick="completeTask({{ task.id }})"
   
   <!-- CORRECT -->
   onclick="completeTask('{{ task.id }}')"
   ```

2. For more complex cases, use data attributes:
   ```html
   <!-- INCORRECT -->
   <div style="width: {{ completion_percentage }}%"></div>
   
   <!-- CORRECT -->
   <div id="progress-bar-fill" data-percentage="{{ completion_percentage }}" style="width: 0%"></div>
   ```
   Then in JavaScript:
   ```js
   const progressBarFill = document.getElementById('progress-bar-fill');
   if (progressBarFill) {
       const percentage = progressBarFill.getAttribute('data-percentage');
       progressBarFill.style.width = percentage + '%';
   }
   ```

3. For complex data, use JSON serialization:
   ```html
   <!-- INCORRECT -->
   const subjectData = {
       {% for subject_id, stats in subject_stats.items() %}
           "{{ subject_id }}": {
               name: "{{ stats.name }}",
               completed: {{ stats.completed }},
               total: {{ stats.total }}
           }{% if not loop.last %},{% endif %}
       {% endfor %}
   };
   
   <!-- CORRECT -->
   const subjectDataJson = '{{ subject_stats|tojson|safe }}';
   const subjectData = JSON.parse(subjectDataJson);
   ```

4. For DOM interactions with Jinja variables, use the data attribute pattern with event listeners:
   ```html
   <!-- INCORRECT -->
   <div onclick="updateValue({{ item.id }}, {{ item.value }})">Click me</div>
   
   <!-- CORRECT -->
   <div class="update-trigger" data-id="{{ item.id }}" data-value="{{ item.value }}">Click me</div>
   ```
   Then in JavaScript:
   ```js
   document.querySelectorAll('.update-trigger').forEach(function(element) {
       element.addEventListener('click', function() {
           const id = this.getAttribute('data-id');
           const value = this.getAttribute('data-value');
           updateValue(id, value);
       });
   });
   ```

**Future Best Practices:**
1. Avoid embedding Jinja variables directly in JavaScript expressions
2. Use data attributes for passing simple values to JavaScript
3. For complex data structures, use the `|tojson` filter
4. Separate template logic from JavaScript logic where possible
5. Avoid duplicate HTML attributes, especially class attributes

## Python Module Issues (3/10/2025)

**Issue:** Import "dotenv" could not be resolved in run.py despite being listed in requirements.txt

**Solution:** Installed the python-dotenv package explicitly using pip:
```
pip install python-dotenv
```

**Possible Causes:**
1. Virtual environment may not have been activated
2. The package might have been previously installed but removed
3. Requirements might have been installed incompletely

**Best Practice:**
When setting up a new development environment, always ensure all dependencies are installed:
```
pip install -r requirements.txt
```

And verify imports are working before beginning development.

## Documentation Added (3/10/2025)

**Documentation Created:**
- Created `docs/template_best_practices.md` to formalize the best practices for JavaScript-Template interactions
- Created `docs/linting_guide.md` with setup instructions for Python and JavaScript/HTML linting tools
- Created `docs/testing_guide.md` with testing procedures to catch template syntax issues early
- Created `docs/README.md` as a central index for all documentation

**Documentation Contents:**
1. Common issues and their solutions
2. Best practices for handling template variables in JavaScript
3. Examples of correct implementation patterns
4. Testing and validation recommendations
5. Linting setup instructions
6. Testing procedures and examples

**Tools Created:**
- Implemented `app/utils/template_validator.py` to automatically scan templates for syntax issues
- Created `.flake8` configuration file for Python linting
- Created `.pre-commit-config.yaml` for pre-commit hooks including template validation

**Validation Results:**
- Ran the template validator script which confirmed no template syntax issues in the current templates
- This verifies that our fixes to the main templates (index.html, progress.html, curriculum.html) were successful

**Purpose:**
The documentation and tools provide a comprehensive foundation for maintaining code quality and preventing future issues. This supports all the "Next Steps" outlined in activeContext.md by:

1. Establishing consistent patterns for frontend-backend data exchange
2. Providing tools for identifying template syntax issues
3. Creating standardized testing procedures
