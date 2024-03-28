# Recruitment App Backend

This Flask application serves as the backend for a recruitment platform, designed to facilitate job postings, applications, and user management. Deployed on Azure, it leverages cloud scalability, security, and performance to provide an efficient and reliable service.

## Getting Started

These instructions will guide you through setting up the project on your local machine for development and testing, and eventually deploying it to Azure for production.

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.12
- pip
- Virtualenv (recommended)
- Azure CLI
- MongoDB (either local installation or a cloud instance)
- An Azure account for deployment

### Installation

Follow these steps to get your development environment running:

1. **Clone the repository**
    ```bash
    git clone https://github.com/MahmoudGh01/Back.git
    cd Back
    ```

2. **Set up a virtual environment** (optional but recommended)
    ```bash
    virtualenv venv
    source venv/bin/activate  # On Windows, use `.\venv\Scripts\activate`
    ```

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

### Running Locally

To run the application locally:

    ```bash
    flask run
    ```

## Deployment on Azure

To deploy the application on Azure:

1. **Log in to Azure CLI**
    ```bash
    az login
    ```

2. **Create Azure resources**
    Follow Azure documentation to set up an App Service plan, create a Web App, and deploy the application. Adjust the commands according to your project requirements.

## API Usage

The backend API's endpoints are documented with Swagger, accessible at /api/docs. This interface allows for easy testing and integration. Here are some of the key endpoints:

/accept-application/{application_id} (PUT): Accept a job application.
/add_quiz (POST): Add a new quiz for job screening.
/all_quiz (GET): Retrieve all quizzes.
/apply-for-job (POST): Submit an application for a job.
/jobss (POST): Create a new job posting.
/details/{detail_id} (GET, PUT, DELETE): Manage job details.
/edit-user/{user_id} (PUT): Edit user details.
/signin (POST): Sign in a user.
/signup (POST): Register a new user.
For a complete list of endpoints and their functionalities, refer to the Swagger documentation hosted at /api/docs.



## Authors

- **Mahmoud Gharbi** - *Initial Work* - [MahmoudGh01](https://github.com/MahmoudGh01)



## Acknowledgments

- Hat tip to anyone whose code was used
- Inspiration
- etc.
