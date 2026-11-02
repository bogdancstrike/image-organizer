# Library search relevance

Search does not pad results to a minimum count. Compound known concepts must each have supporting
visual, tag or text evidence. Stored exact tags and OCR matches provide inspectable explanations.

Indoor locations also use contextual prompts: a room, a person in that room, and the room behind
a subject. Support must beat a corresponding generic-room baseline and competing indoor locations.
This recovers room context behind a dominant subject without accepting every indoor photograph.
The same comparison enriches automatic room tags; tag cache version 3 refreshes on the next analysis.

Read-only regression on a 1,029-photo library with SigLIP 2: kitchen results increased from 1 to 23;
`dog in a snow` and `dog in kitchen` still returned zero. The weakest recovered kitchen examples
were visually checked for visible cabinets, counters and appliances. This is a local regression,
not a measured precision/recall benchmark across all rooms or datasets. Synthetic tests distinguish
a kitchen background, a bedroom, an unspecified room and a query with a missing subject.
