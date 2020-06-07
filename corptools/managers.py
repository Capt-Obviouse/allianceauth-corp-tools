from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import logging

from esi.clients import esi_client_factory
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo, EveAllianceInfo
from . import providers

logger = logging.getLogger(__name__)


class EveNameManager(models.Manager):
    
    def get_or_create_from_esi(self, eve_id):
        """gets or creates with ESI"""
        try:
            entity = self.get(eve_id=eve_id)
            created = False
        except ObjectDoesNotExist:
            entity, created = self.update_or_create_from_esi(eve_id)
        return entity, created

    def create_bulk_from_esi(self, eve_ids):
        """gets bulk names with ESI"""
        if len(eve_ids) > 0:
            from corptools.models import EveName
            response = providers.esi.client.Universe.post_universe_names(
                        ids=eve_ids
                    ).results()
            new_names = []
            for entity in response:
                new_names.append(EveName(
                                eve_id=entity['id'],
                                name=entity['name'],
                                category=entity['category']
                            ))
            self.bulk_create(new_names, ignore_conflicts=True)
            return True
        return True

    def update_or_create_from_esi(self, eve_id):
        """updates or create with ESI"""        
        try:
            response = providers.esi.client.Universe.post_universe_names(
                        ids=[eve_id]
                    ).result()
            entity, created = self.update_or_create(
                eve_id=response[0]['id'],
                defaults={
                    'name': response[0]['name'],
                    'category': response[0]['category'],
                }
            ) 
        except Exception as e:
            logger.exception('ESI Error id {} - {}'.format(eve_id, e))
            raise e
        return entity, created

    def update_or_create_from_eve_model(self, eve_id):
        """updates or create character/corporation/alliancename models from an EveCharacter or falls over to ESI to do so"""
        
        try:
            character = EveCharacter.objects.get_character_by_id(eve_id)
            alliance = None
            if not character.alliance_id:
                alliance, created_alli = self.update_or_create(
                    eve_id=character.alliance_id,
                    defaults={
                        'name': character.alliance_name,
                        'category': self.ALLIANCE,
                    }
                )

            corporation, created_corp = self.update_or_create(
                eve_id=character.corporation_id,
                defaults={
                    'name': character.corporation_name,
                    'category': self.CORPORATION,
                    'alliance':alliance
                }
            )

            character, created = self.update_or_create(
                eve_id=character.character_id,
                defaults={
                    'name': character.character_name,
                    'category': self.CHARACTER,
                    'corporation': corporation,
                    'alliance': alliance
                }
            )
        
        except ObjectDoesNotExist as e:
            logger.exception('Failed to create name: {} - {}'.format(eve_id, e)) # TODO Fallback to ESI
            raise e

        return character, created


class EveItemTypeManager(models.Manager):
    
    def get_or_create_from_esi(self, eve_id):
        """gets or creates with ESI"""
        try:
            entity = self.get(type_id=eve_id)
            created = False
        except ObjectDoesNotExist:
            entity, created = self.update_or_create_from_esi(eve_id)
        return entity, created

    def create_bulk_from_esi(self, eve_ids):
        """gets or creates with ESI"""
        from corptools.task_helpers.update_tasks import process_bulk_types_from_esi
        created = process_bulk_types_from_esi(eve_ids)       
        return created

    def update_or_create_from_esi(self, eve_id):
        """updates or create with ESI"""        
        from corptools.models import EveItemGroup, EveItemDogmaAttribute

        try:
            response, dogma = providers.esi._get_eve_type(eve_id, False)
            group, created = EveItemGroup.objects.get_or_create_from_esi(response.group_id)
            entity, created = self.update_or_create(
                type_id=response.type_id,
                defaults={
                    'name': response.name,
                    'group': group,
                    'description': response.description,
                    'mass': response.mass,
                    'packaged_volume': response.packaged_volume,
                    'portion_size': response.portion_size,
                    'volume': response.volume,
                    'published': response.published,
                    'radius': response.radius,
                }
            )        
            dogma_query = EveItemDogmaAttribute.objects.filter(eve_type_id=response.type_id)
            if dogma_query.exists():
                dogma_query._raw_delete(dogma_query.db) # speed and we are not caring about f-keys or signals on these models 

            EveItemDogmaAttribute.objects.bulk_create(dogma, batch_size=1000, ignore_conflicts=True)  # bulk create
        except Exception as e:
            logger.exception('ESI Error id {} - {}'.format(eve_id, e))
            raise e
        return entity, created

class EveGroupManager(models.Manager):
    
    def get_or_create_from_esi(self, eve_id):
        """gets or creates with ESI"""
        try:
            entity = self.get(group_id=eve_id)
            created = False
        except ObjectDoesNotExist:
            entity, created = self.update_or_create_from_esi(eve_id)
        return entity, created
        
    def update_or_create_from_esi(self, eve_id):
        """updates or create with ESI"""        
        from corptools.models import EveItemCategory

        try:
            response = providers.esi._get_group(eve_id, False)
            category, created = EveItemCategory.objects.get_or_create_from_esi(response.category_id)
            entity, created = self.update_or_create(
                group_id=response.group_id,
                defaults={
                    'name': response.name,
                    'category': category,
                }
            ) 
        except Exception as e:
            logger.exception('ESI Error id {} - {}'.format(eve_id, e))
            raise e
        return entity, created

class EveCategoryManager(models.Manager):
    
    def get_or_create_from_esi(self, eve_id):
        """gets or creates with ESI"""
        try:
            entity = self.get(category_id=eve_id)
            created = False
        except ObjectDoesNotExist:
            entity, created = self.update_or_create_from_esi(eve_id)
        return entity, created
        
    def update_or_create_from_esi(self, eve_id):
        """updates or create with ESI"""        
        try:
            response = providers.esi._get_category(eve_id, False)
            entity, created = self.update_or_create(
                category_id=response.category_id,
                defaults={
                    'name': response.name,
                }
            ) 
        except Exception as e:
            logger.exception('ESI Error id {} - {}'.format(eve_id, e))
            raise e
        return entity, created


class AuditCharacterQuerySet(models.QuerySet):
    def visible_to(self, user):
        # superusers get all visible
        if user.is_superuser:
            logger.debug('Returning all characters for superuser %s.' % user)
            return self

        if user.has_perm('corptools.global_hr'):
            logger.debug('Returning all characters for %s.' % user)
            return self

        try:
            char = user.profile.main_character
            assert char
            # build all accepted queries
            queries = [models.Q(character__character_ownership__user=user)]
            if user.has_perm('corptools.alliance_hr'):
                if char.alliance_id is not None:
                    queries.append(models.Q(character__alliance_id=char.alliance_id))
                else:
                    queries.append(models.Q(character__corporation_id=char.corporation_id))
            if user.has_perm('corptools.corp_hr'):
                if user.has_perm('corptools.alliance_hr'):
                    pass
                else:
                    queries.append(models.Q(character__corporation_id=char.corporation_id))
            logger.debug('%s queries for user %s visible chracters.' % (len(queries), user))
            # filter based on queries
            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug('User %s has no main character. Nothing visible.' % user)
            return self.none()        


class AuditCharacterManager(models.Manager):
    def get_queryset(self):
        return AuditCharacterQuerySet(self.model, using=self._db)

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)
