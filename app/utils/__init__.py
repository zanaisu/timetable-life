# Import utility modules for easy access
from app.utils.task_generator import (
    generate_task_for_subject,
    generate_replacement_task,
    select_weighted_topic,
    add_subtopics_to_task,
    get_subject_distribution_for_week
)

from app.utils.database_helpers import (
    get_subject_code,
    generate_topic_key,
    generate_subtopic_key
)

from app.utils.data_import import (
    import_curriculum_data,
    seed_default_data
)
