# Raw Passages — doi:10.1109/msr66628.2025.00043


## P001

- **Section:** I. INTRODUCTION

- **Relevance:** challenge

- **Text:**

> Neural models trained on noisy datasets inevitably internalize and potentially propagate low-quality reviews into the generated review comments.


## P002

- **Section:** I. INTRODUCTION

- **Relevance:** benefit

- **Text:**

> By retaining only the valid comments predicted by LLMs (i.e., cleaned datasets), the training size is 25% - 66% smaller than the original dataset. Nonetheless, the smaller data did not negatively impact the performance of comment generation models. Instead, the models fine-tuned on the cleaned datasets achieved BLEU-4 scores 7.5% - 13% higher than those trained on the original dataset, with a 12.4% - 13.0% increase specifically on valid comments in test sets.


## P003

- **Section:** VII. DISCUSSIONS

- **Relevance:** challenge

- **Text:**

> We observe that LLMs often incorrectly classify comments including domain-specific terms but do not provide improvement suggestions as valid.


## P004

- **Section:** VII. DISCUSSIONS

- **Relevance:** benefit

- **Text:**

> We observe that the general-purpose CodeT5 model with a cleaned dataset achieved comparable performance (BLEU-4 of 5.67) to the original CodeReviewer (BLEU-4 of 5.73) while using far fewer resources.
