"""Only External Repos url specific constants module"""
from robottelo.config import settings


REPOS_URL = settings.robottelo.repos_hosting_url

CUSTOM_FILE_REPO = 'https://fixtures.pulpproject.org/file/'
CUSTOM_KICKSTART_REPO = 'http://ftp.cvut.cz/centos/8/BaseOS/x86_64/kickstart/'
CUSTOM_RPM_REPO = 'https://fixtures.pulpproject.org/rpm-signed/'
CUSTOM_RPM_SHA_512 = 'https://fixtures.pulpproject.org/rpm-with-sha-512/'
FAKE_5_YUM_REPO = 'http://{0}:{1}@rplevka.fedorapeople.org/fakerepo01/'
FAKE_YUM_DRPM_REPO = 'https://fixtures.pulpproject.org/drpm-signed/'
FAKE_YUM_SRPM_REPO = 'https://fixtures.pulpproject.org/srpm-signed/'
FAKE_YUM_SRPM_DUPLICATE_REPO = 'https://fixtures.pulpproject.org/srpm-duplicate/'
FAKE_YUM_MD5_REPO = 'https://fixtures.pulpproject.org/rpm-with-md5/'
FAKE_7_PUPPET_REPO = 'http://{0}:{1}@rplevka.fedorapeople.org/fakepuppet01/'
# Fedora's OSTree repo changed to a single repo at
#   https://kojipkgs.fedoraproject.org/compose/ostree/repo/
# With branches for each version. Some tests (test_positive_update_url) still need 2 repos URLs,
# We will use the archived versions for now, but probably need to revisit this.
FEDORA26_OSTREE_REPO = 'https://kojipkgs.fedoraproject.org/compose/ostree-20190207-old/26/'
FEDORA27_OSTREE_REPO = 'https://kojipkgs.fedoraproject.org/compose/ostree-20190207-old/26/'
OSTREE_REPO = 'https://fixtures.pulpproject.org/ostree/small/'
FAKE_0_YUM_REPO_STRING_BASED_VERSIONS = (
    'https://fixtures.pulpproject.org/rpm-string-version-updateinfo/'
)
