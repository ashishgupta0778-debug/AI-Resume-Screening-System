async function screenResume() {

    const fileInput =
        document.getElementById("resumeFile");

    const status =
        document.getElementById("status");

    const result =
        document.getElementById("result");


    // Check file
    if (fileInput.files.length === 0) {

        status.innerText =
            "Please select a PDF resume.";

        return;
    }


    const file =
        fileInput.files[0];


    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );


    status.innerText =
        "⏳ Screening resume...";


    result.innerHTML = "";


    try {

        const response =
            await fetch(
                "http://127.0.0.1:8000/screen-resume",
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                "API request failed"
            );
        }


        result.innerHTML = `

            <div class="result-header">

                <div>
                    <h2>Candidate Results</h2>

                    <p>
                        Resume:
                        <b>${data.resume}</b>
                    </p>
                </div>

            </div>


            <!-- Score Cards -->

            <div class="score-grid">

                <div class="score-card">

                    <h3>Skill Score</h3>

                    <div class="score">
                        ${data.skill_score}%
                    </div>

                </div>


                <div class="score-card">

                    <h3>Rule-Based Score</h3>

                    <div class="score">
                        ${data.rule_based_score}
                    </div>

                </div>


                <div class="score-card">

                    <h3>TF-IDF Score</h3>

                    <div class="score">
                        ${data.tfidf_score}
                    </div>

                </div>


                <div class="score-card">

                    <h3>Combined Score</h3>

                    <div class="score">
                        ${data.combined_score}
                    </div>

                </div>

            </div>


            <!-- Candidate Information -->

            <div class="info-grid">


                <div class="info-card">

                    <h3>Candidate Skills</h3>

                    <ul>

                        ${data.candidate_skills
                            .map(
                                skill =>
                                `<li>${skill}</li>`
                            )
                            .join("")}

                    </ul>

                </div>


                <div class="info-card">

                    <h3>Matched Skills</h3>

                    <ul>

                        ${data.matched_skills
                            .map(
                                skill =>
                                `<li>${skill}</li>`
                            )
                            .join("")}

                    </ul>

                </div>


                <div class="info-card">

                    <h3>Experience</h3>

                    <p>
                        ${data.experience}
                    </p>

                    <p>
                        <b>Experience Match:</b>
                        ${data.experience_match}
                    </p>

                </div>


                <div class="info-card">

                    <h3>Education</h3>

                    <p>
                        ${data.education.join(", ")}
                    </p>

                    <p>
                        <b>Education Match:</b>
                        ${data.education_match}
                    </p>

                </div>


            </div>

        `;


        status.innerText =
            "✅ Resume screening completed successfully.";

    }


    catch (error) {

        status.innerText =
            "❌ Error connecting to the FastAPI server.";

        console.error(error);

    }

}