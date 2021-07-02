from kh_common.config import credentials; credentials.db = { }
from kh_common.sql.query import Field, Join, JoinType, Operator, Order, Query, Table, Value, Where
from typing import Any, List, Tuple, Union
import pytest


class TestQuery :

	@pytest.mark.parametrize(
		'value, expected, expected_param',
		[
			(
				Value('test'),
				'%s',
				'test',
			),
			(
				Value(1),
				'%s',
				1,
			),
			(
				Value(1, 'count'),
				'count(%s)',
				1,
			),
		],
	)
	def test_Value_str(self, value: Value, expected: str, expected_param: Any) :
		# act
		result = str(value)
		params = value.params()

		# assert
		assert result == expected
		assert params == expected_param


	@pytest.mark.parametrize(
		'field, expected',
		[
			(
				Field('test1', 'test2'),
				'test1.test2',
			),
			(
				Field('test1', 'test2', 'lower'),
				'lower(test1.test2)',
			),
		],
	)
	def test_Field_str(self, field: Field, expected: str) :
		# act
		result = str(field)

		# assert
		assert result == expected


	@pytest.mark.parametrize(
		'where, expected, expected_params',
		[
			(
				Where(
					Field('test', 'test'),
					Operator.equal,
					Field('test', 'test2'),
				),
				'test.test = test.test2',
				[],
			),
			(
				Where(
					Field('test', 'test'),
					Operator.greater_than,
					Value(1),
				),
				'test.test > %s',
				[1],
			),
			(
				Where(
					Value(1),
					Operator.greater_than_equal_to,
					Value(2),
				),
				'%s >= %s',
				[1, 2],
			),
			(
				Where(
					Value(1),
					Operator.is_null,
					Value(2),
				),
				'%s IS NULL',
				[1],
			),
		],
	)
	def test_Where_str(self, where: Where, expected: str, expected_params: List[Any]) :
		# act
		result = str(where)
		params = where.params()

		# assert
		assert result == expected
		assert params == expected_params


	@pytest.mark.parametrize(
		'args, expected',
		[
			(
				('kheina.test.test',),
				'kheina.test.test',
			),
			(
				('kheina.test.test', 't'),
				'kheina.test.test AS t',
			),
		],
	)
	def test_Table_str(self, args: Tuple[str], expected: str) :
		# act
		table = Table(*args)
		result = str(table)

		# assert
		assert result == expected


	@pytest.mark.parametrize(
		'table_name',
		[
			'.test.test',
			'kheina.test',
		],
	)
	def test_Table_Errors(self, table_name: str) :
		# act
		with pytest.raises(AssertionError) :
			Table(table_name)


	@pytest.mark.parametrize(
		'args, where, expected, expected_params',
		[
			(
				(JoinType.inner, Table('kheina.test.test')),
				[Where(Value(1), Operator.equal, Value(2))],
				'INNER JOIN kheina.test.test ON %s = %s',
				[1, 2],
			),
			(
				(JoinType.outer, Table('kheina.test.test', 't')),
				[Where(Value(1), Operator.equal, Value(2)), Where(Value(3), Operator.equal, Value(4))],
				'FULL OUTER JOIN kheina.test.test AS t ON %s = %s AND %s = %s',
				[1, 2, 3, 4],
			),
		],
	)
	def test_Join_str(self, args: Tuple[Union[JoinType, Table]], where: List[Where], expected: str, expected_params: List[Any]) :
		# act
		join = Join(*args)
		join.where(*where)
		result = str(join)
		params = join.params()

		# assert
		assert result == expected
		assert params == expected_params


	def test_Query_NoSelect(self) :
		# arrange
		query = Query(Table('kheina.test.test'))

		# act
		with pytest.raises(AssertionError) :
			query.__build_query__()


	def test_Query_str(self) :
		# arrange
		query = Query(
			Table('kheina.test.test'),
		).select(
			Field('test', 'test'),
			Field('test', 'test2'),
		).where(
			Where(
				Value(1),
				Operator.not_in,
				Value(2),
			),
			Where(
				Value(3),
				Operator.less_than,
				Value(4),
			),
		).join(
			Join(
				JoinType.cross,
				Table('kheina.test.test1'),
			).where(
				Where(
					Value(5),
					Operator.less_than_equal_to,
					Value(6),
				),
			),
			Join(
				JoinType.left,
				Table('kheina.test.test2'),
			).where(
				Where(
					Value(7),
					Operator.not_equal,
					Query(
						Table('kheina.test.test3')
					).select(
						Field('test3', 'test'),
					).where(
						Where(
							Value(8),
							Operator.within,
							Value(9),
						),
					).function(
						'all'
					),
				),
			),
		).group(
			Field('test', 'test'),
			Field('test', 'test2'),
		).order(
			Field('test', 'test'),
			Order.ascending,
		).having(
			Where(
				Value(10),
				Operator.not_like,
				Value(11),
			),
		).limit(
			12
		).offset(
			13
		)

		# act
		sql, params = query.build()

		# assert
		assert sql == ' '.join([
			'SELECT test.test,test.test2',
			'FROM kheina.test.test',
			'CROSS JOIN kheina.test.test1 ON %s <= %s',
			'LEFT JOIN kheina.test.test2 ON %s !=',
			'all(SELECT test3.test FROM kheina.test.test3 WHERE %s IN %s)',
			'WHERE %s NOT IN %s AND %s < %s',
			'GROUP BY test.test,test.test2',
			'HAVING %s NOT LIKE %s',
			'ORDER BY test.test ASC',
			'LIMIT %s',
			'OFFSET %s;',
		])
		assert params == [5, 6, 7, 8, 9, 1, 2, 3, 4, 10, 11, 12, 13]
