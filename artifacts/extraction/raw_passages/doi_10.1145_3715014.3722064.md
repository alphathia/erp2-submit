# Raw Passages — doi:10.1145/3715014.3722064


## P001

- **Section:** 6.6 User Study

- **Relevance:** usage_pattern

- **Text:**

> We conduct a user study to evaluate the functionality, generalizability, and overall satisfaction of GPIoT for IoT application development. Specifically, with GPIoT deployed on an edge server, we invite 5 experts and 15 non-experts in IoT and ask them to freely express their requirements for any IoT application development that requires signal processing or AI technologies.


## P002

- **Section:** 6.6 User Study

- **Relevance:** benefit

- **Text:**

> As shown in Fig. 23, we observe: 1) GPIoT significantly outperforms the baselines in terms of OCP and US. The main reason is that, tuned on our IoT-specialized datasets, GPIoT can generate code containing more dedicated algorithms with better performance.


## P003

- **Section:** 6.6 User Study

- **Relevance:** challenge

- **Text:**

> GPIoT gets a lower GE score as it performs requirement transformation and code generation for each decomposed task. Nevertheless, we can enhance its efficiency by adopting various LLM inference and serving optimization methods


## P004

- **Section:** 3 SYSTEM OVERVIEW

- **Relevance:** capability_claim

- **Text:**

> GPIoT first leverages Task Decomposition SLM (TDSLM) to decompose the IoT application into multiple manageable sub-tasks with detailed descriptions. Next, through CoT-based prompting techniques, the sub-task descriptions will be gradually transformed into well-structured specifications by Requirement Transformation SLM (RTSLM)


## P005

- **Section:** 3 SYSTEM OVERVIEW

- **Relevance:** interaction_mode

- **Text:**

> Code Generation SLM (CGSLM) accordingly generates a code snippet with documentation. Users can execute the code sequentially to realize the IoT application based on the instructions from the documentation.
