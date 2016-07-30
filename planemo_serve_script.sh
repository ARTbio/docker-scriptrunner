planemo serve --galaxy_branch dev \
    --conda_auto_init \
    --conda_dependency_resolution \
    --conda_auto_install \
    --conda_ensure_channels scrapinghub \
    --tool_data_table tool_data_table_conf.xml.sample.test "$@"
