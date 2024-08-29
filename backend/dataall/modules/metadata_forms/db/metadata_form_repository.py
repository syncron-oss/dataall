from sqlalchemy import or_, and_
from dataall.modules.metadata_forms.db.enums import MetadataFormVisibility
from dataall.modules.metadata_forms.db.metadata_form_models import MetadataForm, MetadataFormField


class MetadataFormRepository:
    @staticmethod
    def create_metadata_form(session, data=None):
        mf: MetadataForm = MetadataForm(
            name=data.get('name'),
            description=data.get('description'),
            SamlGroupName=data.get('SamlGroupName'),
            visibility=data.get('visibility'),
            homeEntity=data.get('homeEntity'),
        )
        session.add(mf)
        session.commit()
        return mf

    @staticmethod
    def get_metadata_form(session, uri):
        return session.query(MetadataForm).get(uri)

    @staticmethod
    def query_metadata_forms(session, is_da_admin, groups, env_uris, org_uris, filter):
        """
        Returns a list of metadata forms based on the user's permissions and any provided filters.
        DataAll admins can see allll forms, while non-admins can only see forms they have access to based on their group memberships.
        :param session:
        :param is_da_admin: is user dataall admin
        :param groups: user's group memberships
        :param env_uris: user's environment URIs
        :param org_uris: user's organization URIs
        :param filter:
        """

        query = session.query(MetadataForm)

        if not is_da_admin:
            query = query.filter(
                or_(
                    MetadataForm.SamlGroupName.in_(groups),
                    MetadataForm.visibility == MetadataFormVisibility.Global.value,
                    and_(
                        MetadataForm.visibility == MetadataFormVisibility.Team.value,
                        MetadataForm.homeEntity.in_(groups),
                    ),
                    and_(
                        MetadataForm.visibility == MetadataFormVisibility.Organization.value,
                        MetadataForm.homeEntity.in_(org_uris),
                    ),
                    and_(
                        MetadataForm.visibility == MetadataFormVisibility.Environment.value,
                        MetadataForm.homeEntity.in_(env_uris),
                    ),
                )
            )

        if filter and filter.get('search_input'):
            query = query.filter(
                or_(
                    MetadataForm.name.ilike('%' + filter.get('search_input') + '%'),
                    MetadataForm.description.ilike('%' + filter.get('search_input') + '%'),
                )
            )
        return query.order_by(MetadataForm.name)

    @staticmethod
    def get_metadata_form_fields(session, form_uri):
        return (
            session.query(MetadataFormField)
            .filter(MetadataFormField.metadataFormUri == form_uri)
            .order_by(MetadataFormField.displayNumber)
            .all()
        )

    @staticmethod
    def create_metadata_form_field(session, uri, data):
        field: MetadataFormField = MetadataFormField(
            metadataFormUri=uri,
            name=data.get('name'),
            description=data.get('description'),
            type=data.get('type'),
            required=data.get('required', False),
            glossaryNodeUri=data.get('glossaryNodeUri', None),
            possibleValues=data.get('possibleValues', None),
            displayNumber=data.get('displayNumber'),
        )
        session.add(field)
        session.commit()
        return field

    @staticmethod
    def get_metadata_form_field_by_uri(session, uri):
        return session.query(MetadataFormField).get(uri)

    @staticmethod
    def update_metadata_form_field(session, fieldUri, data):
        mf = MetadataFormRepository.get_metadata_form_field_by_uri(session, fieldUri)
        mf.name = data.get('name', mf.name)
        mf.description = data.get('description', mf.description)
        mf.type = data.get('type', mf.type)
        mf.glossaryNodeUri = data.get('glossaryNodeUri', mf.glossaryNodeUri)
        mf.required = data.get('required', mf.required)
        mf.possibleValues = data.get('possibleValues', mf.possibleValues)
        mf.displayNumber = data.get('displayNumber', mf.displayNumber)
        session.commit()
        return mf

    @staticmethod
    def get_metadata_form_owner(session, uri):
        return session.query(MetadataForm).get(uri).SamlGroupName