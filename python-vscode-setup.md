# Python Project Setup in VS Code with venv (Ubuntu)

## Step-by-Step Guide

1. `cd /path/to/your/repo`

2. `code .`

3. Open terminal in VS Code (press `Ctrl` and `` ` `` keys together)

4. `python3 -m venv venv`

5. `source venv/bin/activate`

6. Press `Ctrl+Shift+P`, type `Python: Select Interpreter`, press Enter, then select `./venv/bin/python3`

7. `pip install --upgrade pip`

8. `pip install -r requirements.txt` (if you have this file, otherwise skip)

9. Install packages you need: `pip install package-name` (like `pip install requests`)

10. `echo "venv/" >> .gitignore`

11. `pip freeze > requirements.txt`

12. `git add .`

13. `git commit -m "Setup venv"`

14. `git push`

15. When done working, deactivate the virtual environment: `deactivate`

---

## Notes

- **Steps 1-6** are setup (do once)
- **Steps 7-9** are installing packages (do when you need new packages)
- **Steps 10-14** are saving your work to GitHub
- **Step 15** is when you're finished and want to close the virtual environment

## What is venv?

A virtual environment (venv) keeps your project's Python packages separate from other projects. This prevents conflicts between different projects that might need different versions of the same package.

## Tips

- Always activate your venv (`source venv/bin/activate`) before working on your project
- You'll see `(venv)` in your terminal when it's activated
- Remember to deactivate when you're done working
- Never commit the `venv/` folder to GitHub (that's why we add it to `.gitignore`)
