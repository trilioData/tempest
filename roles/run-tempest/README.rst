Run Tempest

**Role Variables**

.. zuul:rolevar:: devstack_base_dir
   :default: /opt/stack

   The devstack base directory.

.. zuul:rolevar:: tempest_concurrency
   :default: 0

   The number of parallel test processes.

.. zuul:rolevar:: tempest_test_regex
   :default: ''

   A regular expression used to select the tests.

   It works only when used with some specific tox environments
   ('all', 'all-plugin'.)

   Multi-line and commented regexs can be achieved by doing this:

       ::
           vars:
             tempest_test_regex: |
               (?x)    # Ignore comments and whitespaces
               # Line with only a comment.
               (tempest\.(api|scenario|thirdparty)).*$    # Run only api scenario and third party

.. zuul:rolevar:: tempest_test_blacklist

   Specifies a blacklist file to skip tests that are not needed.

   Pass a full path to the file.

.. zuul:rolevar:: tox_envlist
   :default: smoke

   The Tempest tox environment to run.

.. zuul:rolevar:: tempest_black_regex
   :default: ''

   A regular expression used to skip the tests.

   It works only when used with some specific tox environments
   ('all', 'all-plugin'.)

   Multi-line and commented regexs can be achieved by doing this:

       ::
           vars:
             tempest_black_regex: |
               (?x)    # Ignore comments and whitespaces
               # Line with only a comment.
               (tempest.api.identity).*$

.. zuul:rolevar:: tox_extra_args
   :default: ''

   String of extra command line options to pass to tox.

   Here is an example of running tox with --sitepackages option:

       ::
           vars:
             tox_extra_args: --sitepackages

.. zuul:rolevar:: tempest_test_timeout
   :default: ''

   The timeout (in seconds) for each test.
