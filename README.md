# cs432_m3

# Virtual Environment Setup

To ensure the project runs in an isolated environment, it is recommended to use a Python virtual environment (`venv`). Follow the steps below to set up the virtual environment:

## 1. Create the Virtual Environment
In the root of the project directory, run the following command to create a new virtual environment:

```bash
python3 -m venv venv
```

## 2. Activate the Virtual Environment
- **For macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

- **For Windows**:
  ```bash
  venv\Scripts\activate
  ```

After activation, your terminal prompt will change to indicate that the virtual environment is active.

## 3. Install Dependencies
Once the virtual environment is activated, install the required dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

This ensures all necessary libraries and modules for the project are installed in the isolated environment.

## 4. Deactivating the Virtual Environment
When you're done working on the project, you can deactivate the virtual environment by running:

```bash
deactivate
```

This will return you to your system’s global Python environment.

